from ultimate_fix_report_generator import UltimateFixReportGenerator

# 初始化生成器
gen = UltimateFixReportGenerator()

# 处理数据并做终极修复
results = gen.process_test_data_with_ultimate_fixes(
    folder_path="data/1",   # 你的CSV目录
    group_name="测试者A",
    age=65
)

# 生成HTML模板
template = gen.generate_corrected_html_template()

# 替换模板里的 {{变量}}
for k, v in results.items():
    template = template.replace(f"{{{{{k}}}}}", str(v))

# 保存报告
with open("ultimate_gait_report.html", "w", encoding="utf-8") as f:
    f.write(template)

print("✅ 终极修复版报告已生成: ultimate_gait_report.html")