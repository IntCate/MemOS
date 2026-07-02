import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Literal, Optional
from datetime import datetime
from langchain_core.messages import (
    SystemMessage, ToolMessage, AIMessage
)

from app.engineering.llm.agent.agent_state import AgentState
from app.core.logger import logger


@dataclass
class ToolCall:
    """工具调用请求"""
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    call_id: str = field(default_factory=lambda: str(hash(datetime.now())))
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """工具执行结果"""
    call_id: str
    success: bool
    content: str
    tool_name: Optional[str] = None
    error: Optional[str] = None
    raw_result: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class AgentNodes:
    """智能体节点逻辑集合：支持线性/非线性自动分流"""
    
    def __init__(self, llm_with_tools):
        self.llm_with_tools = llm_with_tools

    async def reasoning_node(self, state: AgentState) -> Dict[str, Any]:
        """核心推理节点：决定行动方案"""
        logger.info(f"[Agent] 正在进行第 {state['loop_count']+1} 轮推理...")
        logger.debug(f"[Agent] reasoning_node 输入消息: {[msg.content[:10000] + '...' if len(msg.content) > 1000 else msg.content for msg in state['messages']]}")
        
        from app.engineering.prompt import prompt_engine, PromptMode
        result = prompt_engine.render_by_mode(PromptMode.AGENT)
        system_prompt = result.content if result.success else "你是一个强大的AI助手，能够使用工具来完成各种任务。"
        
        # 创建消息副本，避免修改原始状态
        msgs = state["messages"].copy()
        if not any(isinstance(m, SystemMessage) for m in msgs):
            msgs = [SystemMessage(content=system_prompt)] + msgs

        response = await self.llm_with_tools.ainvoke(msgs)
        
        # 只返回新生成的消息，让 LangGraph 通过 operator.add 自动累加
        return {
            "messages": [response],
            "loop_count": state["loop_count"]
        }

    async def execute_linear_node(self, state: AgentState) -> Dict[str, Any]:
        """线性任务节点：支持【结果动态注入】的顺序执行"""
        last_msg = state["messages"][-1]
        tool_calls = getattr(last_msg, 'tool_calls', [])
        
        results = []
        # 维护一个当前轮次的工具执行结果映射表
        execution_context = {}
        
        logger.info(f"[Agent] 进入线性执行模式，共 {len(tool_calls)} 个任务")
        logger.debug(f"[Agent] execute_linear_node 输入消息: {[msg.content[:1000] + '...' if len(msg.content) > 1000 else msg.content for msg in state['messages']]}")

        for i, tc in enumerate(tool_calls):
            original_args = tc.get('args', {})
            injected_args = self._inject_variables(original_args, execution_context)
            tc['args'] = injected_args
            
            tool_call = ToolCall(tool_name=tc['name'], arguments=tc['args'], call_id=tc.get('id', f"call_{i}"))
            result = await self._execute_tool(tool_call)
            
            result_msg = ToolMessage(content=result.content, tool_call_id=tc.get('id'))
            result_msg.tool_index = i
            results.append(result_msg)
            
            execution_context[f"tool_{i}"] = result.content
            
        # 只返回新生成的消息，让 LangGraph 通过 operator.add 自动累加
        return {
            "messages": results,
            "loop_count": state["loop_count"] + 1
        }

    async def execute_nonlinear_node(self, state: AgentState) -> Dict[str, Any]:
        """非线性任务节点：真正的并发并行执行"""
        last_msg = state["messages"][-1]
        tool_calls = getattr(last_msg, 'tool_calls', [])
        
        logger.info(f"[Agent] 进入非线性模式，并行执行 {len(tool_calls)} 个任务")
        logger.debug(f"[Agent] execute_nonlinear_node 输入消息: {[msg.content[:1000] + '...' if len(msg.content) > 1000 else msg.content for msg in state['messages']]}")
        
        async def _run_single_tool(tc, tool_index):
            tool_call = ToolCall(tool_name=tc['name'], arguments=tc.get('args', {}), call_id=tc.get('id', f"call_{tool_index}"))
            result = await self._execute_tool(tool_call)
            result_msg = ToolMessage(content=result.content, tool_call_id=tc.get('id'))
            result_msg.tool_index = tool_index
            return result_msg
        
        tasks = []
        for i, tc in enumerate(tool_calls):
            tasks.append(_run_single_tool(tc, tool_index=i))
        
        results = await asyncio.gather(*tasks)
        
        # 只返回新生成的消息，让 LangGraph 通过 operator.add 自动累加
        return {
            "messages": results,
            "loop_count": state["loop_count"] + 1
        }

    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """执行工具调用
        
        当前已移除 ToolEngine，由 capabilities 层接管工具执行。
        后续可通过 MCPCapability 或 SkillManager 实现具体工具执行逻辑。
        """
        logger.warning(f"[Agent] 工具执行未实现: {tool_call.tool_name}")
        return ToolResult(
            call_id=tool_call.call_id,
            success=False,
            content="",
            error=f"工具执行功能已迁移至 capabilities 层，{tool_call.tool_name} 暂不可用",
            tool_name=tool_call.tool_name
        )

    def _inject_variables(self, args: Dict, context: Dict) -> Dict:
        """将参数中的占位符 {{tool_N}} 替换为 context 中的实际值"""
        if not context:
            return args
        
        # 将 Dict 转为字符串进行全局替换，处理嵌套结构
        args_str = json.dumps(args, ensure_ascii=False)
        
        for key, value in context.items():
            placeholder = "{{" + key + "}}"
            if placeholder in args_str:
                # 如果结果是简单的字符串，直接替换；如果是复杂对象，可以考虑更复杂的逻辑
                # 这里简单处理：将结果转为字符串注入
                args_str = args_str.replace(placeholder, str(value))
        
        return json.loads(args_str)

    def should_continue(self, state: AgentState) -> Literal["execute_linear", "execute_nonlinear", "end"]:
        """决策路由：根据任务特征分流执行路径"""
        logger.debug(f"[Agent] should_continue 输入消息: {[msg.content[:1000] + '...' if len(msg.content) > 1000 else msg.content for msg in state['messages']]}")
        # 从后往前查找，找到最近的包含 tool_calls 的消息（即 reasoning_node 产生的决策）
        tool_calls_msg = None
        for msg in reversed(state["messages"]):
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                tool_calls_msg = msg
                break
        
        # 如果找不到包含 tool_calls 的消息，或者循环次数达到上限，返回 end
        if not tool_calls_msg or state["loop_count"] >= 10:
            return "end"
        
        tool_calls = tool_calls_msg.tool_calls

        # 判断是否需要线性执行
        # 场景1：只有一个工具调用 -> 线性执行即可
        if len(tool_calls) == 1:
            return "execute_linear"
        
        # 场景2：检查工具参数中是否存在 {{tool_N}} 占位符引用
        has_dependency = False
        for tc in tool_calls:
            args_str = json.dumps(tc.get('args', {}))
            if re.search(r"\{\{tool_\d+\}\}", args_str):
                has_dependency = True
                break
        
        if has_dependency:
            return "execute_linear"
        
        # 场景3：无依赖且有多个调用 -> 并行执行
        return "execute_nonlinear"

    async def reflect_node(self, state: AgentState) -> Dict[str, Any]:
        """反思节点：提取关键信息并评估任务完成度"""
        logger.info(f"[Agent] 正在进行结果反思...")
        logger.debug(f"[Agent] reflect_node 输入消息: {[msg.content[:1000] + '...' if len(msg.content) > 1000 else msg.content for msg in state['messages']]}")
        
        tool_results = []
        for msg in reversed(state["messages"]):
            if isinstance(msg, ToolMessage):
                tool_results.append(msg)
            elif hasattr(msg, 'tool_calls') and msg.tool_calls:
                break
        
        if tool_results:
            reflection_content = self._analyze_tool_results(tool_results)
            reflection_msg = AIMessage(
                content=f"<reflection>\n{reflection_content}\n</reflection>"
            )
            # 只返回新生成的消息，让 LangGraph 通过 operator.add 自动累加
            return {"messages": [reflection_msg], "loop_count": state["loop_count"]}
        
        return {"messages": [], "loop_count": state["loop_count"]}

    def _analyze_tool_results(self, tool_results: List[ToolMessage]) -> str:
        """分析工具执行结果的内部逻辑（保持原逻辑，可按需微调）"""
        # ... 原有的结果统计代码 ...
        success_count = sum(1 for r in tool_results if "error" not in r.content.lower())
        return f"本轮成功执行 {success_count}/{len(tool_results)} 个工具，信息{'已更新' if success_count > 0 else '获取失败'}。"
