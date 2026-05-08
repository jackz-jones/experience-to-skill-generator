#!/usr/bin/env python3
"""
会话分析脚本 - 分析OpenClaw会话历史，提取有价值的工作经验
"""

import json
import re
import os
import hashlib
from datetime import datetime
from typing import Dict, List, Any
from collections import Counter, defaultdict
import numpy as np

# 模拟向量数据库功能
class VectorAnalyzer:
    """向量分析器基类（模拟深度学习）"""
    
    def __init__(self):
        self.problem_patterns = {
            "blockchain": {
                "keywords": ["区块链", "gas", "BSC", "ETH", "智能合约", "Tokenview", "监控"],
                "score_weight": 1.5,  # 区块链问题价值更高
                "solution_templates": ["go-zero", "API集成", "定时任务", "数据库存储"]
            },
            "backend": {
                "keywords": ["Go", "Golang", "Python", "API", "数据库", "服务器"],
                "score_weight": 1.2,
                "solution_templates": ["架构设计", "代码实现", "性能优化", "错误处理"]
            },
            "ai_tools": {
                "keywords": ["AI", "自动化", "技能", "OpenClaw", "Agent", "生成"],
                "score_weight": 1.3,
                "solution_templates": ["技能开发", "对话解析", "模板生成", "质量评估"]
            },
            "devops": {
                "keywords": ["Docker", "部署", "运维", "CI/CD", "服务器", "配置"],
                "score_weight": 1.1,
                "solution_templates": ["容器化", "自动化部署", "监控", "故障恢复"]
            }
        }
        
    def classify_problem(self, text: str) -> Dict:
        """问题分类算法"""
        text_lower = text.lower()
        scores = {}
        
        for category, config in self.problem_patterns.items():
            score = 0
            for keyword in config["keywords"]:
                if keyword.lower() in text_lower:
                    score += 1
            
            if score > 0:
                scores[category] = score * config["score_weight"]
        
        # 归一化
        total = sum(scores.values())
        if total > 0:
            scores = {k: v/total for k, v in scores.items()}
        
        return {
            "primary_category": max(scores, key=scores.get) if scores else "general",
            "confidence_scores": scores,
            "category_count": len(scores)
        }
        
    def extract_key_phrases(self, text: str) -> List[str]:
        """提取关键短语"""
        # 简单实现：提取包含技术关键词的短句
        phrases = []
        sentences = re.split(r'[。！？.!?]', text)
        
        all_keywords = []
        for config in self.problem_patterns.values():
            all_keywords.extend(config["keywords"])
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 5:
                continue
                
            # 检查是否包含关键词
            has_keyword = any(keyword.lower() in sentence.lower() for keyword in all_keywords)
            
            if has_keyword and len(sentence) < 100:
                phrases.append(sentence)
        
        return phrases[:5]

class QualityScorer:
    """技能质量评分器"""
    
    def __init__(self):
        self.quality_factors = {
            "clarity": {"weight": 0.25, "desc": "清晰度"},
            "completeness": {"weight": 0.25, "desc": "完整性"},
            "actionability": {"weight": 0.30, "desc": "可操作性"},
            "technical_depth": {"weight": 0.20, "desc": "技术深度"}
        }
        
    def score_conversation(self, user_msg: str, assistant_msg: str) -> Dict:
        """评分对话质量"""
        scores = {}
        
        # 清晰度评分
        clarity_score = self._score_clarity(user_msg, assistant_msg)
        
        # 完整性评分（是否有完整解决方案）
        completeness_score = self._score_completeness(assistant_msg)
        
        # 可操作性评分（是否有具体步骤）
        actionability_score = self._score_actionability(assistant_msg)
        
        # 技术深度评分
        technical_score = self._score_technical_depth(assistant_msg)
        
        scores = {
            "clarity": clarity_score,
            "completeness": completeness_score,
            "actionability": actionability_score,
            "technical_depth": technical_score
        }
        
        # 计算总分
        weighted_total = sum(
            scores[factor] * self.quality_factors[factor]["weight"] 
            for factor in scores
        )
        
        scores["total_score"] = weighted_total
        scores["grade"] = self._get_grade(weighted_total)
        
        return scores
        
    def _score_clarity(self, user_msg: str, assistant_msg: str) -> float:
        """清晰度评分"""
        # 用户问题是否清晰
        user_clarity = min(len(user_msg.strip().split()), 50) / 50.0
        
        # 助手回复是否结构化
        if '\n' in assistant_msg or '：' in assistant_msg or any(\
            num in assistant_msg for num in ['1.', '2.', '3.', '首先', '其次', '最后']):
            structure_score = 1.0
        else:
            structure_score = 0.5
        
        return (user_clarity * 0.4 + structure_score * 0.6)
        
    def _score_completeness(self, assistant_msg: str) -> float:
        """完整性评分"""
        completeness_indicators = [
            "解决方案", "方法", "步骤", "实现", "配置", 
            "代码", "示例", "文档", "测试", "验证"
        ]
        
        msg_lower = assistant_msg.lower()
        score = min(sum(1 for indicator in completeness_indicators \
                       if indicator in msg_lower), 5) / 5.0
        
        return score
        
    def _score_actionability(self, assistant_msg: str) -> float:
        """可操作性评分"""
        # 检查是否有具体步骤或命令
        actionable_patterns = [
            r'\d+\.\s+[^\n]+',  # 编号步骤
            r'首先[^\n]+然后[^\n]+最后',  # 顺序描述
            r'执行命令', '运行脚本', '安装依赖', '配置参数'
        ]
        
        matches = sum(1 for pattern in actionable_patterns \
                      if re.search(pattern, assistant_msg, re.IGNORECASE))
        
        return min(matches, 5) / 5.0
        
    def _score_technical_depth(self, assistant_msg: str) -> float:
        """技术深度评分"""
        technical_keywords = [
            "API", "数据库", "架构", "算法", "并发", "缓存",
            "分布式", "微服务", "容器", "自动化", "脚本", "调试"
        ]
        
        msg_lower = assistant_msg.lower()
        tech_count = sum(1 for keyword in technical_keywords \
                         if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', msg_lower))
        
        return min(tech_count, 8) / 8.0
        
    def _get_grade(self, score: float) -> str:
        """评分等级"""
        if score >= 0.9:
            return "S+ (卓越)"
        elif score >= 0.8:
            return "A (优秀)"
        elif score >= 0.7:
            return "B (良好)"
        elif score >= 0.6:
            return "C (合格)"
        else:
            return "D (需要改进)"

def analyze_conversation_history(conversation_history: List[Dict]) -> Dict[str, Any]:
    """
    分析会话历史，提取问题模式、解决方案和最佳实践
    
    Args:
        conversation_history: 会话历史记录列表
        
    Returns:
        分析结果字典，包含问题模式、解决方案、最佳实践等
    """
    
    if not conversation_history:
        return {"error": "会话历史为空"}
    
    print(f"🔍 DEBUG: 开始分析，共有 {len(conversation_history)} 条记录")
    
    # 提取关键信息
    user_messages = []
    assistant_messages = []
    tool_calls = []
    
    for idx, msg in enumerate(conversation_history):
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        print(f"  [{idx}] role={role}, content_len={len(str(content))}")
        
        if role == "user":
            user_messages.append(content)
        elif role == "assistant":
            assistant_messages.append(content)
        elif role == "tool":
            if "tool_calls" in content:
                tool_calls.extend(content.get("tool_calls", []))
            elif isinstance(content, dict):
                # 尝试提取工具调用信息
                tool_calls.append(content)
            elif content:
                # 作为简单工具记录
                tool_calls.append({"raw": str(content)[:100]})

    print(f"✅ DEBUG: 提取结果 - 用户消息: {len(user_messages)}, 助手消息: {len(assistant_messages)}, 工具调用: {len(tool_calls)}")
    
    # 问题模式识别
    problem_patterns = identify_problem_patterns(user_messages)
    
    # 解决方案提取
    solutions = extract_solutions(user_messages, assistant_messages, tool_calls)
    
    # 复杂性评估
    complexity = assess_complexity(user_messages, assistant_messages, tool_calls)
    
    # 创建分析总结
    analysis_summary = {
        "summary": {
            "total_messages": len(conversation_history),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "tool_calls": len(tool_calls),
            "analysis_time": datetime.now().isoformat()
        },
        "problem_patterns": problem_patterns,
        "solutions": solutions,
        "complexity": complexity
    }
    
    print(f"📊 DEBUG: 分析完成 - 问题模式: {len(problem_patterns)}, 解决方案: {len(solutions)}")
    
    # ⭐ 技术深化：添加深度学习分析
    print("🧠 启动高级分析...")
    
    # 1. 向量分析器
    vector_analyzer = VectorAnalyzer()
    quality_scorer = QualityScorer()
    
    # 2. 分析每个对话片段
    enhanced_solutions = []
    for i, (user_msg, assistant_msg) in enumerate(zip(user_messages, assistant_messages)):
        if i < len(solutions):
            solution = solutions[i]
        else:
            solution = {"problem": user_msg[:100], "solution": assistant_msg[:200]}
        
        # 问题分类
        classification = vector_analyzer.classify_problem(user_msg)
        
        # 关键短语提取
        key_phrases = vector_analyzer.extract_key_phrases(user_msg + " " + assistant_msg)
        
        # 质量评分
        quality_scores = quality_scorer.score_conversation(user_msg, assistant_msg)
        
        # 增强解决方案数据
        enhanced_solution = {
            **solution,
            "classification": classification,
            "key_phrases": key_phrases,
            "quality_scores": quality_scores,
            "hash_id": hashlib.md5((user_msg + assistant_msg).encode()).hexdigest()[:12]
        }
        
        enhanced_solutions.append(enhanced_solution)
    
    # 3. 高级分析统计
    categories_count = Counter()
    quality_grades = Counter()
    phrase_frequency = Counter()
    
    for sol in enhanced_solutions:
        primary_cat = sol.get("classification", {}).get("primary_category", "general")
        categories_count[primary_cat] += 1
        
        grade = sol.get("quality_scores", {}).get("grade", "D (需要改进)")
        quality_grades[grade] += 1
        
        for phrase in sol.get("key_phrases", []):
            phrase_frequency[phrase] += 1
    
    # 4. 专业度评估
    professional_score = _calculate_professional_score(enhanced_solutions)
    
    # 5. 更新分析结果
    analysis_summary["advanced_analysis"] = {
        "categories_distribution": dict(categories_count),
        "quality_distribution": dict(quality_grades),
        "top_key_phrases": dict(phrase_frequency.most_common(10)),
        "professional_score": professional_score,
        "enhanced_solutions": enhanced_solutions,
        "analysis_model": "VectorAnalyzer + QualityScorer v1.0"
    }
    
    print(f"✅ 高级分析完成 - 专业度评分: {professional_score['total_score']:.2f}/10.0")
    
    return analysis_summary

def _calculate_professional_score(self, solutions: List[Dict]) -> Dict:
    """计算专业度评分"""
    # 这里模拟计算专业度，实际应该更复杂
    total_quality = sum(sol.get("quality_scores", {}).get("total_score", 0) for sol in solutions)
    avg_quality = total_quality / len(solutions) if solutions else 0
    
    # 技术深度加分
    tech_depths = sum(sol.get("quality_scores", {}).get("technical_depth", 0) for sol in solutions)
    avg_tech_depth = tech_depths / len(solutions) if solutions else 0
    
    # 分类多样性
    categories = set(sol.get("classification", {}).get("primary_category", "") for sol in solutions)
    diversity_score = len(categories) / 4.0  # 假设最多4个类别
    
    # 计算总分 (10分制)
    total_score = (avg_quality * 5.0) + (avg_tech_depth * 3.0) + (diversity_score * 2.0)
    
    professional_level = "S+ (专家级)" if total_score > 8.0 else \
                        "A (专业级)" if total_score > 6.0 else \
                        "B (熟练级)" if total_score > 4.0 else \
                        "C (入门级)" if total_score > 2.0 else "D (新手级)"
    
    return {
        "total_score": round(total_score, 2),
        "professional_level": professional_level,
        "components": {
            "avg_quality": round(avg_quality, 2),
            "avg_tech_depth": round(avg_tech_depth, 2),
            "diversity_score": round(diversity_score, 2)
        },
        "recommendation": _get_professional_recommendation(total_score)
    }

def _calculate_professional_score(solutions: List[Dict]) -> Dict:
    """计算专业度评分"""
    if not solutions:
        return {
            "total_score": 0.0,
            "professional_level": "D (新手级)",
            "components": {"avg_quality": 0.0, "avg_tech_depth": 0.0, "diversity_score": 0.0},
            "recommendation": "暂无数据"
        }
    
    # 技术深度加分
    total_quality = sum(sol.get("quality_scores", {}).get("total_score", 0) for sol in solutions)
    avg_quality = total_quality / len(solutions)
    
    tech_depths = sum(sol.get("quality_scores", {}).get("technical_depth", 0) for sol in solutions)
    avg_tech_depth = tech_depths / len(solutions)
    
    # 分类多样性
    categories = set(sol.get("classification", {}).get("primary_category", "") for sol in solutions)
    diversity_score = min(len(categories) / 4.0, 1.0)  # 假设最多4个类别
    
    # 计算总分 (10分制)
    total_score = (avg_quality * 5.0) + (avg_tech_depth * 3.0) + (diversity_score * 2.0)
    
    professional_level = "S+ (专家级)" if total_score > 8.0 else \
                        "A (专业级)" if total_score > 6.0 else \
                        "B (熟练级)" if total_score > 4.0 else \
                        "C (入门级)" if total_score > 2.0 else "D (新手级)"
    
    return {
        "total_score": round(total_score, 2),
        "professional_level": professional_level,
        "components": {
            "avg_quality": round(avg_quality, 2),
            "avg_tech_depth": round(avg_tech_depth, 2),
            "diversity_score": round(diversity_score, 2)
        },
        "recommendation": _get_professional_recommendation(total_score)
    }

def _get_professional_recommendation(score: float) -> str:
    """根据评分给出专业建议"""
    if score >= 8.0:
        return "🔬 技术深度极佳，建议开发SaaS产品或技术咨询服务"
    elif score >= 6.0:
        return "💼 专业水平突出，可产品化为工具或培训课程"
    elif score >= 4.0:
        return "🛠️ 技能组合良好，可开发插件或自动化脚本"
    elif score >= 2.0:
        return "📚 基础扎实，建议专注某个技术栈深度发展"
    else:
        return "🎯 需要技术积累，从具体问题解决开始"

    
    return {
        "summary": {
            "total_messages": len(conversation_history),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "tool_calls": len(tool_calls),
            "time_range": extract_time_range(conversation_history)
        },
        "problem_patterns": problem_patterns,
        "solutions": solutions,
        "complexity": complexity,
        "is_skill_candidate": evaluate_skill_candidate(problem_patterns, solutions, complexity)
    }

def identify_problem_patterns(user_messages: List[str]) -> List[Dict]:
    """识别问题模式"""
    patterns = []
    
    # 常见问题关键词
    problem_keywords = {
        "config": ["配置", "设置", "setup", "config"],
        "error": ["错误", "报错", "error", "failed", "cannot"],
        "debug": ["调试", "排查", "debug", "troubleshoot"],
        "howto": ["如何", "怎么", "怎样", "how to", "how do"],
        "performance": ["性能", "慢", "卡", "performance", "slow"],
        "integration": ["集成", "连接", "integration", "connect"]
    }
    
    for msg in user_messages:
        msg_patterns = []
        for pattern_name, keywords in problem_keywords.items():
            for keyword in keywords:
                if keyword in msg.lower():
                    msg_patterns.append(pattern_name)
                    break
        
        if msg_patterns:
            # 提取问题描述
            problem_desc = extract_problem_description(msg)
            patterns.append({
                "message": msg[:100] + "..." if len(msg) > 100 else msg,
                "patterns": list(set(msg_patterns)),
                "description": problem_desc,
                "urgency": assess_urgency(msg)
            })
    
    return patterns

def extract_problem_description(message: str) -> str:
    """从消息中提取问题描述"""
    # 简单提取：去除问候语和冗余信息
    lines = message.split('\n')
    for line in lines:
        if len(line.strip()) > 10 and not line.strip().startswith(('你好', '您好', 'hi', 'hello')):
            return line.strip()[:200]
    return message[:100]

def assess_urgency(message: str) -> str:
    """评估问题紧急程度"""
    urgency_keywords = {
        "high": ["紧急", "马上", "立刻", "urgent", "immediately", "ASAP"],
        "medium": ["今天", "尽快", "尽快", "today", "soon"],
        "low": ["有空", "方便时", "when convenient"]
    }
    
    msg_lower = message.lower()
    for level, keywords in urgency_keywords.items():
        for keyword in keywords:
            if keyword in msg_lower:
                return level
    
    return "unknown"

def extract_solutions(user_msgs: List[str], assistant_msgs: List[str], tool_calls: List[Dict]) -> List[Dict]:
    """从对话中提取解决方案"""
    solutions = []
    
    # 匹配问题和对应的回答
    for i, user_msg in enumerate(user_msgs[:len(assistant_msgs)]):
        if i < len(assistant_msgs):
            assistant_msg = assistant_msgs[i]
            solution = {
                "problem": user_msg[:100],
                "solution": assistant_msg[:200],
                "contains_code": contains_code(assistant_msg),
                "contains_commands": contains_commands(assistant_msg),
                "tool_usage": extract_tool_usage_for_solution(tool_calls, i)
            }
            solutions.append(solution)
    
    return solutions

def contains_code(text: str) -> bool:
    """检查是否包含代码"""
    code_patterns = [
        r'```\w+',  # 代码块开始
        r'def\s+\w+',  # 函数定义
        r'class\s+\w+',  # 类定义
        r'\w+\s*=\s*[^=]',  # 变量赋值
        r'\.\w+\(',  # 方法调用
    ]
    
    for pattern in code_patterns:
        if re.search(pattern, text):
            return True
    return False

def contains_commands(text: str) -> bool:
    """检查是否包含命令"""
    command_patterns = [
        r'`[^`]+`',  # 反引号内的代码
        r'\./[\w/]+',  # 可执行文件路径
        r'\b(make|run|test|build)\b',  # 常见命令
        r'\$[^$]+\$',  # 命令行标记
    ]
    
    for pattern in command_patterns:
        if re.search(pattern, text):
            return True
    return False

def extract_tool_usage_for_solution(tool_calls: List[Dict], solution_index: int) -> List[str]:
    """提取解决方案用到的工具"""
    tools_used = []
    for tool in tool_calls:
        if isinstance(tool, dict) and "name" in tool:
            tools_used.append(tool["name"])
    return list(set(tools_used))[:5]  # 返回前5个不重复的工具

def assess_complexity(user_msgs: List[str], assistant_msgs: List[str], tool_calls: List[Dict]) -> Dict:
    """评估任务复杂度"""
    # 消息数量
    total_msgs = len(user_msgs) + len(assistant_msgs)
    
    # 工具调用复杂度
    unique_tools = len(set(tool.get("name", "") for tool in tool_calls if isinstance(tool, dict)))
    
    # 代码复杂度
    total_code_blocks = sum(1 for msg in assistant_msgs if contains_code(msg))
    
    # 命令复杂度
    total_commands = sum(1 for msg in assistant_msgs if contains_commands(msg))
    
    # 综合评估
    complexity_score = (
        (total_msgs / 10) +  # 每10条消息加1分
        (unique_tools * 2) +  # 每个唯一工具加2分
        (total_code_blocks * 1.5) +  # 每个代码块加1.5分
        (total_commands * 0.5)  # 每个命令加0.5分
    )
    
    if complexity_score > 20:
        complexity_level = "high"
    elif complexity_score > 10:
        complexity_level = "medium"
    else:
        complexity_level = "low"
    
    return {
        "score": round(complexity_score, 2),
        "level": complexity_level,
        "total_messages": total_msgs,
        "unique_tools": unique_tools,
        "code_blocks": total_code_blocks,
        "commands": total_commands
    }

def extract_time_range(conversation_history: List[Dict]) -> Dict:
    """提取会话时间范围"""
    if not conversation_history:
        return {"start": None, "end": None}
    
    # 寻找时间戳（这里简化处理）
    first_msg = conversation_history[0]
    last_msg = conversation_history[-1]
    
    return {
        "start": first_msg.get("timestamp", "unknown"),
        "end": last_msg.get("timestamp", "unknown")
    }

def evaluate_skill_candidate(problem_patterns: List[Dict], solutions: List[Dict], complexity: Dict) -> bool:
    """评估是否适合创建为skill"""
    
    if not problem_patterns or not solutions:
        return False
    
    # 条件1: 问题重复出现
    unique_patterns = set()
    for pattern in problem_patterns:
        unique_patterns.update(pattern.get("patterns", []))
    
    # 条件2: 解决方案完整
    has_complete_solution = any(
        sol.get("contains_code", False) or 
        sol.get("contains_commands", False) or 
        len(sol.get("tool_usage", [])) > 0
        for sol in solutions
    )
    
    # 条件3: 复杂度足够
    is_complex_enough = complexity.get("level", "low") != "low" or len(solutions) >= 2
    
    # 条件4: 有实际执行内容
    has_executable_content = any(sol.get("contains_code", False) for sol in solutions) or any(sol.get("contains_commands", False) for sol in solutions)
    
    # 最终判断
    return (
        (len(unique_patterns) >= 2) or  # 有2个以上不同问题模式
        (has_complete_solution and is_complex_enough) or  # 完整方案且足够复杂
        (has_executable_content and len(solutions) >= 1)  # 有可执行内容且至少一个方案
    )

if __name__ == "__main__":
    # 测试代码
    test_conversation = [
        {"role": "user", "content": "我的MAC外接了一个HP显示屏，然后插了一个扩展坞，为啥显示器里多出来一个"},
        {"role": "assistant", "content": "收到你的截屏了，让我先检查一下你的显示器设置情况..."},
        {"role": "user", "content": "创建实例脚本"},
        {"role": "assistant", "content": "好的！我来创建这个skill的实例脚本..."}
    ]
    
    result = analyze_conversation_history(test_conversation)
    print("会话分析结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))