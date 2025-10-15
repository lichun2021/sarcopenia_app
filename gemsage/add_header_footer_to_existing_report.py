#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
给现有的GemSage HTML报告添加解放军总医院标准页眉页脚

用法：
    python add_header_footer_to_existing_report.py 输入报告.html 输出报告.html
"""

import sys
import re
from bs4 import BeautifulSoup
import datetime
import random

def add_a4_print_layout(input_html_path, output_html_path, subject_info=None,
                        report_id=None, report_date=None, institution=None,
                        report_title=None, version=None):
    """
    给现有HTML报告添加A4打印布局和页眉页脚

    Parameters:
    -----------
    input_html_path : str
        输入的HTML文件路径
    output_html_path : str
        输出的HTML文件路径
    subject_info : dict, optional
        受试者信息，如果不提供则从HTML中提取
        {'name': '', 'patient_id': '', 'department': '', 'age': '', 'gender': '', 'education': ''}
    report_id : str, optional
        报告编码，如果不提供则自动生成
    report_date : str, optional
        检测时间，如果不提供则使用当前时间
    institution : str, optional
        页眉医疗机构名称（默认：中国人民解放军总医院<br>第二医学中心）
    report_title : str, optional
        报告标题（默认：《身体运动能力测评报告》）
    version : str, optional
        系统版本号（默认：v7.2，仅影响页脚版本显示）
    """

    # 1. 读取原始HTML
    with open(input_html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # 2. 生成报告信息（如果未提供）
    if report_id is None:
        now = datetime.datetime.now()
        report_id = now.strftime('%Y%m%d%H%M%S') + ''.join(random.choices('0123456789ABCDEF', k=4))

    if report_date is None:
        now = datetime.datetime.now()
        report_date = now.strftime('%Y年%m月%d日%H时%M分%S秒')

    # 3. 从HTML中提取受试者信息（如果未提供）
    if subject_info is None:
        subject_info = extract_subject_info_from_html(html_content)

    # 4. 生成A4打印CSS
    a4_print_css = generate_a4_print_css()

    # 5. 生成页眉HTML（使用自定义参数）
    header_kwargs = {}
    if institution is not None:
        header_kwargs['institution'] = institution
    if report_title is not None:
        header_kwargs['report_title'] = report_title

    header_html = generate_header_html(report_id, report_date, subject_info, **header_kwargs)

    # 6. 生成页脚HTML（固定内容，仅版本号可定制）
    footer_html = generate_footer_html(version=version if version else "v7.2")

    # 7. 包装原始内容
    wrapped_html = wrap_existing_content(
        html_content,
        a4_print_css,
        header_html,
        footer_html,
        report_id,
        subject_info
    )

    # 8. 保存输出
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(wrapped_html)

    print(f"✅ 已添加A4打印页眉页脚")
    print(f"   输入: {input_html_path}")
    print(f"   输出: {output_html_path}")
    print(f"   报告编码: {report_id}")
    print(f"   受试者: {subject_info.get('name', '未知')}")


def extract_subject_info_from_html(html_content):
    """从HTML中提取受试者信息"""
    soup = BeautifulSoup(html_content, 'html.parser')

    subject_info = {
        'name': '',
        'patient_id': '',
        'department': '',
        'age': '',
        'gender': '',
        'education': ''
    }

    # 尝试从patient-info或类似结构中提取
    patient_info = soup.find(class_='patient-info')
    if patient_info:
        text = patient_info.get_text()

        # 提取姓名
        name_match = re.search(r'姓名[：:]\s*([^\s]+)', text)
        if name_match:
            subject_info['name'] = name_match.group(1)

        # 提取年龄
        age_match = re.search(r'年龄[：:]\s*(\d+)', text)
        if age_match:
            subject_info['age'] = int(age_match.group(1))

        # 提取性别
        gender_match = re.search(r'性别[：:]\s*([男女])', text)
        if gender_match:
            subject_info['gender'] = gender_match.group(1)

    # 如果没有找到，使用默认值
    if not subject_info['name']:
        subject_info['name'] = '测试者'
    if not subject_info['age']:
        subject_info['age'] = 65
    if not subject_info['gender']:
        subject_info['gender'] = '男'

    return subject_info


def generate_a4_print_css():
    """生成A4打印布局CSS"""
    return """
    /* ==================== A4打印布局 ==================== */
    @media print {
        @page {
            size: A4 portrait;
            margin: 0;
        }

        body {
            margin: 0;
            padding: 0;
        }

        .page-wrapper {
            page-break-inside: avoid;
            padding: 0 15mm;
        }
        
        .original-content {
            padding: 0;
        }

        .print-header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            padding: 8mm 12mm 4mm 12mm;
            background: white;
            z-index: 1000;
        }

        .print-footer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 5mm 15mm;
            background: white;
            z-index: 1000;
        }

        .print-header,
        .print-footer {
            display: block !important;
        }

        .print-header {
            height: 50mm;
        }

        .print-footer {
            height: 25mm;
        }

        /* 避免元素被切开 */
        .section-title, .test-section, table, .data-table {
            break-inside: avoid;
            page-break-inside: avoid;
        }

        thead {
            display: table-header-group;
        }
    }

    @media screen {
        body {
            background: #f5f5f5 !important;
            padding: 20px !important;
        }

        .page-wrapper {
            width: 210mm;
            min-height: 297mm;
            background: white;
            margin: 0 auto 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            position: relative;
            padding: 0;
        }
        
        .original-content {
            padding: 55mm 15mm 30mm 15mm;
        }
    }

    /* 页眉样式 */
    .print-header {
        background: white;
        padding: 8mm 12mm 4mm 12mm;
        border-bottom: 2px solid #2c3e50;
        margin-bottom: 5mm;
    }

    .print-header-report-id {
        font-size: 8pt;
        color: #000;
        text-align: right;
        margin-bottom: 1mm;
    }

    .print-header-institution {
        font-size: 15pt;
        font-weight: bold;
        color: #2c3e50;
        text-align: center;
        line-height: 1.2;
        margin-bottom: 1mm;
    }

    .print-header-report-title {
        font-size: 16pt;
        font-weight: bold;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 2mm;
    }

    .print-header-subject-info {
        font-size: 8pt;
        color: #2c3e50;
        margin-bottom: 0;
    }

    .subject-info-row {
        display: flex;
        justify-content: space-between;
        margin-bottom: 0.3mm;
        line-height: 1.1;
    }

    .info-item {
        flex: 1;
        padding: 0 0.5mm;
        white-space: nowrap;
        overflow: hidden;
    }

    /* 页脚样式 */
    .print-footer {
        background: white;
        padding: 5mm 15mm;
        border-top: 2px solid #ecf0f1;
        margin-top: 10mm;
    }

    .print-footer-top {
        margin-bottom: 2mm;
        font-size: 9pt;
        color: #000;
        line-height: 1.4;
    }

    .print-footer-standards {
        margin-bottom: 1mm;
    }

    .print-footer-standards strong {
        color: #2c3e50;
        font-weight: bold;
    }

    .print-footer-disclaimer {
        font-style: italic;
        color: #000;
    }

    .print-footer-bottom {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 10pt;
        color: #000;
        font-weight: bold;
        padding-top: 2mm;
        border-top: 2px solid #000;
    }

    .print-footer-left {
        display: flex;
        gap: 10px;
    }

    .print-footer-center {
        font-weight: bold;
        color: #2c3e50;
    }

    .print-footer-right {
        text-align: right;
    }

    /* 内容区域 */
    .original-content {
        position: relative;
        z-index: 1;
    }
    """


def generate_header_html(report_id, report_date, subject_info, institution="中国人民解放军总医院<br>第二医学中心", report_title="《身体运动能力测评报告》"):
    """
    生成页眉HTML

    Parameters:
    -----------
    report_id : str
        报告编码
    report_date : str
        检测时间
    subject_info : dict
        受试者信息
    institution : str
        医疗机构名称（支持HTML，如<br>换行）
    report_title : str
        报告标题
    """
    return f"""
    <div class="print-header">
        <div class="print-header-report-id">
            唯一报告编码：（可用于查询详细数据或追溯）：{report_id}
        </div>
        <div class="print-header-institution">
            {institution}
        </div>
        <div class="print-header-report-title">
            {report_title}
        </div>
        <div class="print-header-subject-info">
            <div class="subject-info-row">
                <span class="info-item">姓名：{subject_info.get('name', '')}</span>
                <span class="info-item">就诊号：{subject_info.get('patient_id', '')}</span>
                <span class="info-item">科室：{subject_info.get('department', '')}</span>
            </div>
            <div class="subject-info-row">
                <span class="info-item">年龄：{subject_info.get('age', '')}</span>
                <span class="info-item">性别：{subject_info.get('gender', '')}</span>
                <span class="info-item">教育程度：{subject_info.get('education', '')}</span>
            </div>
            <div class="subject-info-row">
                <span class="info-item">检测时间：{report_date}</span>
                <span class="info-item"></span>
                <span class="info-item"></span>
            </div>
        </div>
    </div>
    """


def generate_footer_html(version="v7.2"):
    """
    生成页脚HTML（固定内容）

    Parameters:
    -----------
    version : str
        系统版本号（默认v7.2）
    """
    return f"""
    <div class="print-footer">
        <div class="print-footer-top">
            <div class="print-footer-standards">
                <strong>参考标准来源:</strong>
                《国民体质测定标准(2023年修订)》, AWGS 2019(步速、五次坐立时间),
                国际文献标准(支撑相差异&lt;10%、COP偏移&lt;2cm), 系统经验阈值(基于1000+样本统计)
            </div>
            <div class="print-footer-disclaimer">
                本报告结果仅供参考，不能替代专业医疗诊断。测试结果受当时受试者身体状态、环境等因素影响。
                建议咨询医生或康复师对结果进行最终解读并制定干预方案。
            </div>
        </div>
        <div class="print-footer-bottom">
            <div class="print-footer-left">
                <span>GemSage {version}</span>
                <span>|</span>
                <span>解放军总医院第二医学中心</span>
            </div>
            <div class="print-footer-center">打印时显示页码</div>
            <div class="print-footer-right">
                机密文件 · 仅供临床参考
            </div>
        </div>
    </div>
    """


def wrap_existing_content(html_content, a4_css, header_html, footer_html, report_id, subject_info):
    """包装现有HTML内容，添加页眉页脚"""

    soup = BeautifulSoup(html_content, 'html.parser')

    # 提取原始的body内容
    original_body = soup.find('body')
    if original_body:
        # 去除重复的标题部分（.header, .hospital-name, .report-title, .patient-info等）
        for redundant_class in ['header', 'hospital-name', 'report-title', 'patient-info', 'report-code']:
            for element in original_body.find_all(class_=redundant_class):
                element.decompose()

        original_content = str(original_body)
        # 移除<body>和</body>标签
        original_content = re.sub(r'</?body[^>]*>', '', original_content)
        
        # 在每个page-break后添加占位div
        original_content = original_content.replace(
            '<div style="page-break-before: always;"></div>',
            '<div style="page-break-before: always;"></div><div style="height: 60mm;"></div>'
        )
    else:
        original_content = html_content

    # 提取原始title
    original_title = soup.find('title')
    title_text = original_title.string if original_title else "身体运动能力测评报告"

    # 提取原始style
    original_styles = []
    for style in soup.find_all('style'):
        original_styles.append(str(style.string) if style.string else '')

    original_style_content = '\n'.join(original_styles)

    # 构建新的HTML
    new_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title_text} - {subject_info.get('name', '')} - {report_id}</title>
    <style>
    {original_style_content}

    {a4_css}
    </style>
</head>
<body>
    {header_html}

    <div class="page-wrapper">
        <!-- 顶部占位，为页眉留出空间 -->
        <div style="height: 60mm;"></div>
        
        <div class="original-content">
            {original_content}
        </div>
        
        <!-- 底部占位，为页脚留出空间 -->
        <div style="height: 30mm;"></div>
    </div>

    {footer_html}

    <script>
    // 可使用 Ctrl+P 或 Cmd+P 打印报告
    </script>
</body>
</html>
    """

    return new_html


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description='给GemSage报告添加解放军总医院标准页眉页脚',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:

  # 基本用法（自动生成输出文件名）
  python add_header_footer_to_existing_report.py 输入报告.html

  # 指定输出文件名
  python add_header_footer_to_existing_report.py 输入.html 输出.html

  # 自定义机构名称
  python add_header_footer_to_existing_report.py 输入.html 输出.html \\
    --institution "北京协和医院"

  # 自定义报告标题
  python add_header_footer_to_existing_report.py 输入.html 输出.html \\
    --title "《步态分析报告》"

  # 自定义版本号
  python add_header_footer_to_existing_report.py 输入.html 输出.html \\
    --version "v8.0"

  # 自定义受试者信息
  python add_header_footer_to_existing_report.py 输入.html 输出.html \\
    --name "张三" --age 65 --gender "男" --patient-id "12345" --department "骨科"

  # 完整自定义
  python add_header_footer_to_existing_report.py 输入.html 输出.html \\
    --name "李四" --age 50 --gender "女" \\
    --institution "北京协和医院" \\
    --title "《康复评估报告》" \\
    --version "v8.0" \\
    --footer-institution "北京协和医院康复科"
        """
    )

    # 必需参数
    parser.add_argument('input', help='输入HTML文件路径')
    parser.add_argument('output', nargs='?', help='输出HTML文件路径（可选，默认自动生成）')

    # 受试者信息
    parser.add_argument('--name', help='姓名')
    parser.add_argument('--age', type=int, help='年龄')
    parser.add_argument('--gender', choices=['男', '女'], help='性别')
    parser.add_argument('--patient-id', dest='patient_id', help='就诊号')
    parser.add_argument('--department', help='科室')
    parser.add_argument('--education', help='教育程度')

    # 报告信息
    parser.add_argument('--report-id', dest='report_id', help='报告编码（默认自动生成）')
    parser.add_argument('--report-date', dest='report_date', help='检测时间（格式：YYYY年MM月DD日HH时MM分SS秒）')

    # 页眉自定义
    parser.add_argument('--institution', help='页眉医疗机构名称（支持\\n换行）')
    parser.add_argument('--title', dest='report_title', help='报告标题')

    # 页脚自定义（仅版本号可定制）
    parser.add_argument('--version', help='系统版本号（默认v7.2）')

    args = parser.parse_args()

    input_path = args.input

    # 如果未指定输出路径，自动生成
    if args.output:
        output_path = args.output
    else:
        base_name = input_path.replace('.html', '')
        output_path = f"{base_name}_带页眉页脚.html"

    # 构建subject_info（如果有参数）
    subject_info = None
    if any([args.name, args.age, args.gender, args.patient_id, args.department, args.education]):
        subject_info = {}
        if args.name:
            subject_info['name'] = args.name
        if args.age:
            subject_info['age'] = args.age
        if args.gender:
            subject_info['gender'] = args.gender
        if args.patient_id:
            subject_info['patient_id'] = args.patient_id
        if args.department:
            subject_info['department'] = args.department
        if args.education:
            subject_info['education'] = args.education

    # 处理换行符
    institution = args.institution.replace('\\n', '<br>') if args.institution else None

    # 执行转换
    add_a4_print_layout(
        input_path, output_path,
        subject_info=subject_info,
        report_id=args.report_id,
        report_date=args.report_date,
        institution=institution,
        report_title=args.report_title,
        version=args.version
    )

    print()
    print("=" * 70)
    print("✅ 完成！")
    print(f"   打开查看: open {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
