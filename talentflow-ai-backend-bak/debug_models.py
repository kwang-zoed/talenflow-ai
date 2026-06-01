#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本：定位 SQLAlchemy Mapper 初始化问题
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("调试脚本：定位模型导入和 Mapper 初始化问题")
print("=" * 60)

# 测试1：检查单个模型导入
print("\n[测试1] 逐个导入模型...")
models_to_test = [
    ("User", "app.models.user"),
    ("Resume", "app.models.resume"),
    ("JobPosition", "app.models.job_position"),
    ("Task", "app.models.task"),
    ("Application", "app.models.application"),
]

for model_name, module_path in models_to_test:
    try:
        module = __import__(module_path, fromlist=[model_name])
        model_class = getattr(module, model_name)
        print(f"✅ {module_path}.{model_name} 导入成功")
    except Exception as e:
        print(f"❌ {module_path}.{model_name} 导入失败: {e}")

# 测试2：检查 SQLAlchemy metadata
print("\n[测试2] 检查 SQLAlchemy Metadata...")
try:
    from sqlmodel import SQLModel
    print(f"✅ SQLModel 导入成功")
    print(f"   - tables: {list(SQLModel.metadata.tables.keys())}")
except Exception as e:
    print(f"❌ SQLModel Metadata 检查失败: {e}")

# 测试3：检查 engine 创建和 mapper 初始化
print("\n[测试3] 检查数据库连接和 Mapper 初始化...")
try:
    from app.core.database import engine
    print(f"✅ engine 创建成功")
    
    # 尝试创建所有表（这会触发 mapper 初始化）
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)
    print("✅ Mapper 初始化成功！所有表创建完成")
    
except Exception as e:
    print(f"❌ Mapper 初始化失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("调试完成")
print("=" * 60)
