# !/usr/bin/env python3
import asyncio
import multiprocessing
import sys
import time
from datetime import datetime
from typing import Any, Dict
from rich.console import Console
from dotenv import load_dotenv
from common.consts import Agents
from local_agents.common.utils import output_results
from local_agents.fingenius.src.config import PROJECT_ROOT
from local_agents.fingenius.src.console import clear_screen, visualizer
from local_agents.fingenius.src.environment.battle import BattleEnvironment
from local_agents.fingenius.src.environment.research import ResearchEnvironment
from local_agents.fingenius.src.logger import logger
from local_agents.fingenius.src.schema import AgentState

load_dotenv()

console = Console()

class EnhancedFinGeniusAnalyzer:
    """Enhanced FinGenius analyzer with beautiful visualization"""
    
    def __init__(self):
        self.start_time = time.time()
        self.total_tool_calls = 0
        self.total_llm_calls = 0

    async def analyze_stock(self, stock_code: str, max_steps: int = 3, debate_rounds: int = 2) -> Dict[str, Any]:
        """Run complete stock analysis with enhanced visualization"""
        try:
            # Clear screen and show logo
            clear_screen()
            visualizer.show_logo()
            
            # Show analysis start
            visualizer.show_section_header("开始股票分析", "🚀")
            visualizer.show_progress_update("初始化分析环境", f"目标股票: {stock_code}")
            
            # Research phase
            visualizer.show_section_header("研究阶段", "🔍")
            research_results = await self._run_research_phase(stock_code, max_steps)
            
            if not research_results:
                visualizer.show_error("研究阶段失败", "无法获取足够的分析数据")
                return {"error": "Research failed", "stock_code": stock_code}
            
            # Show research results
            visualizer.show_research_summary(research_results)
            
            # Battle phase
            visualizer.show_section_header("专家辩论阶段", "⚔️")
            battle_results = await self._run_battle_phase(research_results, max_steps, debate_rounds)
            
            if battle_results:
                visualizer.show_debate_summary(battle_results)

            # Final results
            final_results = self._prepare_final_results(stock_code, research_results, battle_results)
            
            # Show completion
            total_time = time.time() - self.start_time
            visualizer.show_completion(total_time)
            
            return final_results
            
        except Exception as e:
            visualizer.show_error(str(e), "股票分析过程中出现错误")
            logger.error(f"Analysis failed: {str(e)}")
            return {"error": str(e), "stock_code": stock_code}

    async def _run_research_phase(self, stock_code: str, max_steps: int) -> Dict[str, Any]:
        """Run research phase with enhanced visualization"""
        try:
            # Create research environment
            visualizer.show_progress_update("创建研究环境")
            research_env = await ResearchEnvironment.create(max_steps=max_steps)
            
            # Show registered agents
            agent_names = [
                "sentiment_agent",
                "risk_control_agent", 
                "hot_money_agent",
                "technical_analysis_agent",
                "chip_analysis_agent",
                "big_deal_analysis_agent",
            ]
            
            for name in agent_names:
                agent = research_env.get_agent(name)
                if agent:
                    visualizer.show_progress_update(f"注册研究员", f"专家: {agent.name}")
            
            # Run research with tool call visualization
            visualizer.show_progress_update("开始深度研究", "多专家顺序分析中（每3秒一个）...")
            
            # Enhance agents with visualization
            self._enhance_agents_with_visualization(research_env)
            
            results = await research_env.run(stock_code=stock_code)
            
            # Update counters
            if hasattr(research_env, 'tool_calls'):
                self.total_tool_calls += research_env.tool_calls
            if hasattr(research_env, 'llm_calls'):
                self.total_llm_calls += research_env.llm_calls
            
            await research_env.cleanup()
            return results
            
        except Exception as e:
            visualizer.show_error(f"研究阶段错误: {str(e)}")
            return {}

    async def _run_battle_phase(self, research_results: Dict[str, Any], max_steps: int, debate_rounds: int) -> Dict[str, Any]:
        """Run battle phase with enhanced visualization"""
        try:
            # Create battle environment
            visualizer.show_progress_update("创建辩论环境")
            battle_env = await BattleEnvironment.create(max_steps=max_steps, debate_rounds=debate_rounds)
            
            # Register agents for battle
            research_env = await ResearchEnvironment.create(max_steps=max_steps)
            agent_names = [
                "sentiment_agent",
                "risk_control_agent",
                "hot_money_agent", 
                "technical_analysis_agent",
                "chip_analysis_agent",
                "big_deal_analysis_agent",
            ]
            
            for name in agent_names:
                agent = research_env.get_agent(name)
                if agent:
                    agent.current_step = 0
                    agent.state = AgentState.IDLE
                    battle_env.register_agent(agent)
                    visualizer.show_progress_update(f"注册辩论专家", f"专家: {agent.name}")
            
            # Enhance agents with visualization for battle
            self._enhance_battle_agents_with_visualization(battle_env)
            
            # Run battle
            visualizer.show_progress_update("开始专家辩论", "多轮辩论与投票中...")
            results = await battle_env.run(research_results)
            
            # Update counters
            if hasattr(battle_env, 'tool_calls'):
                self.total_tool_calls += battle_env.tool_calls
            if hasattr(battle_env, 'llm_calls'):
                self.total_llm_calls += battle_env.llm_calls
            
            await research_env.cleanup()
            await battle_env.cleanup()
            return results
            
        except Exception as e:
            visualizer.show_error(f"辩论阶段错误: {str(e)}")
            return {}

    def _enhance_agents_with_visualization(self, environment):
        """Simple visualization enhancement without breaking functionality"""
        # Don't override methods - just store agent names for later use
        pass

    def _enhance_battle_agents_with_visualization(self, battle_env):
        """Enhance battle agents with visualization for debate messages"""
        # Instead of overriding methods, we'll enhance the broadcast message method
        if hasattr(battle_env, '_broadcast_message'):
            original_broadcast = battle_env._broadcast_message
            
            async def enhanced_broadcast(sender_id: str, content: str, event_type: str):
                # Show the debate message before broadcasting
                agent_name = battle_env.state.active_agents.get(sender_id, sender_id)
                
                if event_type == "speak":
                    visualizer.show_debate_message(agent_name, content, "speak")
                elif event_type == "vote":
                    visualizer.show_debate_message(agent_name, f"投票 {content}", "vote")
                
                # Call original broadcast
                return await original_broadcast(sender_id, content, event_type)
            
            battle_env._broadcast_message = enhanced_broadcast


    def _prepare_final_results(self, stock_code: str, research_results: Dict[str, Any], battle_results: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare final analysis results"""
        final_results = {
            "stock_code": stock_code,
            "analysis_time": time.time() - self.start_time,
            "total_tool_calls": self.total_tool_calls,
            "total_llm_calls": self.total_llm_calls
        }
        
        # Merge research results
        if research_results:
            final_results['research_summary'] = research_results['summary']
        
        # Add battle insights
        if battle_results and "vote_count" in battle_results:
            votes = battle_results["vote_count"]
            total_votes = sum(votes.values())
            if total_votes > 0:
                bullish_pct = (votes.get("bullish", 0) / total_votes) * 100
                final_results["expert_consensus"] = f"{bullish_pct:.1f}% 看涨"
                final_results["votes"] = votes
                final_results["battle_highlights"] = battle_results['battle_highlights']
                final_results["voted_agents"] = battle_results['voted_agents']
        
        return final_results


async def fingenius_main(stock_code):
    """Main entry point for the application."""
    # add_log_file()
    debate_rounds = 3
    max_steps = 6
    format = 'json'
    output_path = PROJECT_ROOT/f'reports/{datetime.now().strftime("%Y-%m-%d")}/'

    analyzer = None

    try:
        # Create enhanced analyzer
        analyzer = EnhancedFinGeniusAnalyzer()

        # Run analysis with beautiful visualization
        results = await analyzer.analyze_stock(stock_code, max_steps, debate_rounds)
        # results = {}

        # write output results
        output_results(results, stock_code, output_path, Agents.fingenius, format)

        decision = extract_decision(results)
        return decision

    except KeyboardInterrupt:
        visualizer.show_error("分析被用户中断", "Ctrl+C")
        return -1
    except Exception as e:
        visualizer.show_error(f"分析过程中发生错误: {str(e)}")
        logger.error(f"Error during research: {str(e)}")
        return -1
    finally:
        # Clean up resources to prevent warnings
        if analyzer:
            try:
                # Force cleanup of any remaining async resources
                import gc
                gc.collect()
                
                # Give time for cleanup
                await asyncio.sleep(0.1)
            except:
                pass
        print("主程序即将退出，最终清理中...")
        for p in multiprocessing.active_children():
            print(f"正在终止子进程: {p.name}")
            p.terminate()
            p.join()


def extract_decision(results):
    decision = False
    votes = results.get('votes')
    if votes:
        bullish = votes.get('bullish')
        bearish = votes.get('bearish')
        if bullish > bearish:
            decision = True
        print(f"bullish: {bullish}, bearish: {bearish}, decision: {decision}")
    return decision


if __name__ == "__main__":
    stock_code = '600519'
    result = asyncio.run(fingenius_main(stock_code))
    print(result)
    if result == -1:
        sys.exit(1)
    else:
        sys.exit(0)
