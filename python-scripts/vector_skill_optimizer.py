#!/usr/bin/env python3
"""
向量技能优化器 - 技术深化核心模块
实现：向量数据库 + 相似度匹配 + 技能推荐
"""

import json
from typing import List, Dict, Tuple, Any
from collections import defaultdict
import hashlib
import os

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

if NUMPY_AVAILABLE:
    import pickle

class SkillVectorEngine:
    """技能向量引擎"""
    
    def __init__(self, skill_base_path: str = None):
        self.skill_vectors = {}  # skill_id -> vector
        self.skill_metadata = {}  # skill_id -> metadata
        self.skill_categories = defaultdict(list)  # category -> [skill_ids]
        
        # 技能特征维度（技术深化关键）
        self.feature_dimensions = [
            "blockchain_related", "go_language", "python_language", 
            "ai_integration", "devops_deployment", "data_processing",
            "api_design", "database_usage", "automation_level",
            "complexity", "profitability", "time_sensitivity"
        ]
        
        # 加载现有技能库
        if skill_base_path and os.path.exists(skill_base_path):
            self.load_skill_base(skill_base_path)
    
    @staticmethod
    def _pure_zeros(size):
        """纯Python创建零向量"""
        return [0.0] * size

    @staticmethod
    def _pure_norm(vec):
        """纯Python计算向量模长"""
        return sum(x * x for x in vec) ** 0.5

    @staticmethod
    def _pure_dot(vec1, vec2):
        """纯Python计算向量点积"""
        return sum(a * b for a, b in zip(vec1, vec2))

    @staticmethod
    def _pure_normalize(vec):
        """纯Python归一化向量"""
        norm = sum(x * x for x in vec) ** 0.5
        if norm > 0:
            return [x / norm for x in vec]
        return vec

    @staticmethod
    def _pure_mean(values):
        """纯Python计算均值"""
        return sum(values) / len(values) if values else 0.0

    def _zeros(self, size):
        """创建零向量（自动选择numpy或纯Python）"""
        if NUMPY_AVAILABLE:
            return np.zeros(size)
        return self._pure_zeros(size)

    def _norm(self, vec):
        """计算向量模长（自动选择numpy或纯Python）"""
        if NUMPY_AVAILABLE:
            return np.linalg.norm(vec)
        return self._pure_norm(vec)

    def _dot(self, vec1, vec2):
        """计算向量点积（自动选择numpy或纯Python）"""
        if NUMPY_AVAILABLE:
            return np.dot(vec1, vec2)
        return self._pure_dot(vec1, vec2)

    def _normalize(self, vec):
        """归一化向量（自动选择numpy或纯Python）"""
        if NUMPY_AVAILABLE:
            norm = np.linalg.norm(vec)
            return vec / norm if norm > 0 else vec
        return self._pure_normalize(vec)

    def _to_array(self, data):
        """将数据转换为numpy数组或保持列表"""
        if NUMPY_AVAILABLE:
            return np.array(data)
        return list(data)

    def _to_list(self, vec):
        """将向量转换为Python列表"""
        if NUMPY_AVAILABLE and isinstance(vec, np.ndarray):
            return vec.tolist()
        return list(vec)

    def _vector_item(self, vec, index):
        """获取向量中指定索引的值"""
        return vec[index]

    def _set_vector_item(self, vec, index, value):
        """设置向量中指定索引的值"""
        vec[index] = value

    def vectorize_skill(self, skill_content: str, metadata: Dict = None):
        """将技能内容向量化"""
        # 技术深化：特征工程
        features = self._zeros(len(self.feature_dimensions))
        
        content_lower = skill_content.lower()
        
        # 维度1: 区块链相关
        blockchain_keywords = ["区块链", "gas", "bsc", "eth", "智能合约", "tokenview", "转账"]
        features[0] = sum(1 for kw in blockchain_keywords if kw in content_lower) / len(blockchain_keywords)
        
        # 维度2: Go语言
        go_keywords = ["go", "golang", "go-zero", "struct", "interface", "goroutine"]
        features[1] = sum(1 for kw in go_keywords if kw in content_lower) / len(go_keywords)
        
        # 维度3: Python语言
        python_keywords = ["python", "pandas", "numpy", "自动化", "脚本", "数据分析"]
        features[2] = sum(1 for kw in python_keywords if kw in content_lower) / len(python_keywords)
        
        # 维度4: AI集成
        ai_keywords = ["ai", "人工智能", "skill", "openclaw", "agent", "自动化"]
        features[3] = sum(1 for kw in ai_keywords if kw in content_lower) / len(ai_keywords)
        
        # 维度5: DevOps部署
        devops_keywords = ["docker", "部署", "运维", "ci/cd", "服务器", "配置"]
        features[4] = sum(1 for kw in devops_keywords if kw in content_lower) / len(devops_keywords)
        
        # 维度6: 数据处理
        data_keywords = ["数据", "处理", "分析", "excel", "报表", "统计"]
        features[5] = sum(1 for kw in data_keywords if kw in content_lower) / len(data_keywords)
        
        # 维度7: API设计
        api_keywords = ["api", "接口", "rest", "http", "请求", "响应"]
        features[6] = sum(1 for kw in api_keywords if kw in content_lower) / len(api_keywords)
        
        # 维度8: 数据库使用
        db_keywords = ["数据库", "mysql", "postgresql", "redis", "存储", "查询"]
        features[7] = sum(1 for kw in db_keywords if kw in content_lower) / len(db_keywords)
        
        # 维度9: 自动化程度（基于步骤数量）
        step_indicators = ["步骤", "流程", "操作", "命令", "执行", "配置"]
        features[8] = sum(1 for indicator in step_indicators if indicator in content_lower) / len(step_indicators)
        
        # 维度10: 复杂度（基于长度和结构）
        complexity_score = min(len(skill_content.split()) / 500, 1.0)  # 文本长度
        features[9] = complexity_score
        
        # 维度11: 赚钱潜力（基于关键词）
        profit_keywords = ["赚钱", "销售", "定价", "客户", "商业", "收入"]
        features[10] = sum(1 for kw in profit_keywords if kw in content_lower) / len(profit_keywords)
        
        # 维度12: 时间敏感性
        time_keywords = ["实时", "定时", "监控", "预警", "立即", "及时"]
        features[11] = sum(1 for kw in time_keywords if kw in content_lower) / len(time_keywords)
        
        # 归一化向量
        vector = self._normalize(features)
        
        return vector
    
    def add_skill(self, skill_id: str, skill_content: str, metadata: Dict = None):
        """添加技能到向量数据库"""
        vector = self.vectorize_skill(skill_content, metadata)
        self.skill_vectors[skill_id] = vector
        
        # 存储元数据
        self.skill_metadata[skill_id] = metadata or {}
        self.skill_metadata[skill_id]["content_preview"] = skill_content[:200]
        self.skill_metadata[skill_id]["vector_norm"] = float(self._norm(vector))
        
        # 分类存储
        categories = metadata.get("categories", ["general"]) if metadata else ["general"]
        for category in categories:
            self.skill_categories[category].append(skill_id)
        
        print(f"✅ 技能向量化完成: {skill_id} (维度: {len(vector)})")
    
    def find_similar_skills(self, query_content: str, top_k: int = 5, threshold: float = 0.5) -> List[Tuple[str, float, Dict]]:
        """查找相似技能"""
        query_vector = self.vectorize_skill(query_content)
        
        similarities = []
        for skill_id, skill_vector in self.skill_vectors.items():
            similarity = float(self._dot(query_vector, skill_vector))
            if similarity >= threshold:
                similarities.append((skill_id, similarity, self.skill_metadata.get(skill_id, {})))
        
        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def generate_skill_recommendations(self, user_query: str, existing_skills: List[str] = None) -> Dict:
        """生成技能推荐"""
        # 找到相似技能
        similar_skills = self.find_similar_skills(user_query, top_k=3)
        
        # 分析技能缺口
        skill_gaps = self._analyze_skill_gaps(user_query, existing_skills)
        
        # 生成组合建议
        composite_suggestions = self._generate_composite_suggestions(user_query, similar_skills)
        
        return {
            "query": user_query,
            "similar_existing_skills": similar_skills,
            "skill_gaps": skill_gaps,
            "composite_suggestions": composite_suggestions,
            "recommended_skill_template": self._generate_skill_template(user_query, skill_gaps)
        }
    
    def _analyze_skill_gaps(self, query: str, existing_skills: List[str] = None) -> Dict:
        """分析技能缺口"""
        query_vector = self.vectorize_skill(query)
        
        # 分析各维度强度
        dimension_strengths = {}
        for i, dim_name in enumerate(self.feature_dimensions):
            dimension_strengths[dim_name] = float(self._vector_item(query_vector, i))
        
        # 找出弱维度（间隙）
        weak_dimensions = [dim for dim, strength in dimension_strengths.items() if strength < 0.3]
        
        return {
            "dimension_strengths": dimension_strengths,
            "weak_dimensions": weak_dimensions,
            "gap_score": len(weak_dimensions) / len(self.feature_dimensions)
        }
    
    def _generate_composite_suggestions(self, query: str, similar_skills: List) -> List[Dict]:
        """生成组合技能建议"""
        suggestions = []
        
        if similar_skills:
            for skill_id, similarity, metadata in similar_skills:
                suggestion = {
                    "type": "enhance_existing",
                    "skill_id": skill_id,
                    "similarity": float(similarity),
                    "action": f"基于现有技能 '{skill_id}' 增强，相似度 {similarity:.2%}",
                    "improvement_suggestions": [
                        "添加更多具体代码示例",
                        "优化步骤说明清晰度",
                        "增加错误处理机制",
                        "补充测试用例"
                    ]
                }
                suggestions.append(suggestion)
        
        # 添加创新建议
        suggestions.append({
            "type": "innovative_combination",
            "description": "结合区块链监控 + AI自动化",
            "value_proposition": "创建智能区块链监控助手，自动分析链上数据并生成报告",
            "estimated_development_time": "2-3周",
            "potential_revenue": "💎 高价值 (SaaS定价 $99/月)"
        })
        
        suggestions.append({
            "type": "technical_depth_expansion",
            "description": "深化Go-zero + 数据库优化",
            "value_proposition": "开发高性能区块链数据存储和查询引擎",
            "estimated_development_time": "31-4周",
            "potential_revenue": "💼 中等价值 (技术咨询 $5000/项目)"
        })
        
        return suggestions
    
    def _generate_skill_template(self, query: str, skill_gaps: Dict) -> str:
        """生成技能模板"""
        template = f"""# 技能模板 - 基于查询生成

## 查询分析
**用户问题**: {query}

## 技能空缺分析
"""
        
        weak_dims = skill_gaps.get("weak_dimensions", [])
        if weak_dims:
            template += "检测到以下维度需要加强:\n"
            for dim in weak_dims:
                template += f"- **{dim}**: 建议添加相关内容\n"
        else:
            template += "✅ 技能维度覆盖完整\n"
        
        template += """
## 建议的技能结构

### 1. 问题描述
[用户遇到的具体问题，应包含技术细节]

### 2. 解决方案框架
[基于类似问题的解决方案模式]

### 3. 具体实施步骤
1. [步骤1：环境准备]
2. [步骤2：核心配置]
3. [步骤3：代码实现]
4. [步骤4：测试验证]

### 4. 最佳实践建议
- [实践1：性能优化]
- [实践2：错误处理]
- [实践3：扩展性考虑]

### 5. 技术栈推荐
- 主要技术: [根据向量分析推荐]
- 辅助工具: [推荐适合的工具链]
- 测试框架: [测试方案建议]

## 升级建议
基于向量分析，本技能可向以下方向优化：
1. 增加自动化程度
2. 强化技术深度
3. 添加商业化要素
"""
        
        return template
    
    def save_skill_base(self, filepath: str):
        """保存技能向量库"""
        data = {
            "skill_vectors": {k: self._to_list(v) for k, v in self.skill_vectors.items()},
            "skill_metadata": self.skill_metadata,
            "skill_categories": dict(self.skill_categories)
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 技能库已保存: {filepath} (技能数: {len(self.skill_vectors)})")
    
    def load_skill_base(self, filepath: str):
        """加载技能向量库"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.skill_vectors = {k: self._to_array(v) for k, v in data.get("skill_vectors", {}).items()}
        self.skill_metadata = data.get("skill_metadata", {})
        self.skill_categories = defaultdict(list, data.get("skill_categories", {}))
        
        print(f"📂 技能库已加载: {filepath} (技能数: {len(self.skill_vectors)})")
    
    def get_statistics(self) -> Dict:
        """获取技能库统计"""
        total_skills = len(self.skill_vectors)
        categories = list(self.skill_categories.keys())
        avg_vector_norm = self._pure_mean([m.get("vector_norm", 0) for m in self.skill_metadata.values()])
        
        return {
            "total_skills": total_skills,
            "categories": categories,
            "category_distribution": {k: len(v) for k, v in self.skill_categories.items()},
            "avg_vector_norm": float(avg_vector_norm),
            "vector_dimensions": len(self.feature_dimensions)
        }

# 使用示例
if __name__ == "__main__":
    print("🧠 技能向量引擎测试...")
    
    # 1. 创建引擎
    engine = SkillVectorEngine()
    
    # 2. 添加测试技能
    test_skill_1 = """如何用Go实现区块链Gas价格监控
使用go-zero框架，连接Tokenview API
定时获取BSC/ETH的Gas数据
存储到MySQL数据库
设置报警机制"""
    
    test_skill_2 = """Python数据自动化处理脚本
用pandas处理Excel数据
自动生成统计报表
通过邮件发送结果
设置定时任务每天执行"""
    
    test_skill_3 = """AI技能自动化生成工具
分析对话历史
提取问题模式
自动生成技能文档
集成到OpenClaw平台"""
    
    engine.add_skill("blockchain_gas_monitor", test_skill_1, 
                    {"categories": ["blockchain", "golang", "monitoring"]})
    engine.add_skill("python_data_automation", test_skill_2,
                    {"categories": ["python", "data", "automation"]})
    engine.add_skill("ai_skill_generator", test_skill_3,
                    {"categories": ["ai", "automation", "openclaw"]})
    
    # 3. 测试查询
    test_query = """需要开发一个系统，能监控多个区块链的Gas价格，
    还能分析大额转账，最好能自动生成报告。"""
    
    print(f"\n🔍 测试查询: {test_query}")
    recommendations = engine.generate_skill_recommendations(test_query)
    
    # 4. 显示结果
    print("\n📊 推荐结果:")
    for rec_type, recs in [("相似技能", recommendations.get("similar_existing_skills", [])),
                           ("技能缺口", [recommendations.get("skill_gaps", {})]),
                           ("组合建议", recommendations.get("composite_suggestions", []))]:
        print(f"\n{rec_type}:")
        if isinstance(recs, list):
            for rec in recs[:2]:  # 只显示前2个
                print(f"  - {rec}")
        else:
            print(f"  - {recs}")
    
    # 5. 保存技能库
    engine.save_skill_base("/tmp/skill_vector_base.json")
    
    # 6. 显示统计
    stats = engine.get_statistics()
    print(f"\n📈 技能库统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")