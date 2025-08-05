# GemSage 模块修改记录

本文档记录了对第三方 `gemsage` 模块的所有修改，以便在模块更新后能够重新应用这些修改。

## 修改日期
2025-08-05

## 修改的文件

### 1. gemsage/multi_file_workflow.py

#### 新增函数：`generate_reports_from_analyses_json`
**位置：** 文件末尾，`main()` 函数之前

**功能：** 基于JSON数据生成报告（不依赖目录）

**修改内容：**
```python
def generate_reports_from_analyses_json(analysis_results, report_type="combined"):
    """
    基于JSON数据生成报告（不依赖目录）
    
    参数:
        analysis_results: 分析结果列表（JSON格式）
        report_type: 报告类型
            - "individual": 每个分析结果生成一个独立报告
            - "combined": 所有结果合并成一个综合报告
            - "both": 生成独立报告 + 综合报告
    
    返回:
        str: HTML格式的报告内容（如果是单个报告）
        list: HTML格式的报告列表（如果是多个报告）
    """
    if not analysis_results:
        raise ValueError("分析结果不能为空")
    
    generator = FullMedicalReportGenerator()
    generated_reports = []
    
    # 生成独立报告
    if report_type in ["individual", "both"]:
        for i, result in enumerate(analysis_results, 1):
            try:
                # 获取患者信息
                if 'original_patient_info' in result:
                    patient_info = result['original_patient_info']
                else:
                    source_file = result.get('source_file', f'analysis_{i}')
                    basename = os.path.basename(source_file).replace('.csv', '') if source_file else f'patient_{i}'
                    patient_info = {
                        'name': extract_name_from_filename(basename),
                        'gender': '未知',
                        'age': extract_age_from_filename(basename),
                        'id': f'AUTO_{i:03d}'
                    }
                
                # 直接使用原有方法生成报告
                report_html = generator.generate_report_from_algorithm(result, patient_info)
                generated_reports.append(report_html)
                
            except Exception as e:
                raise ValueError(f"报告 {i} 生成失败: {e}")
    
    # 生成综合报告
    if report_type in ["combined", "both"]:
        try:
            # 合并所有分析数据
            combined_result = combine_analysis_results(analysis_results)
            
            # 综合患者信息
            if len(analysis_results) == 1 and 'original_patient_info' in analysis_results[0]:
                combined_patient_info = analysis_results[0]['original_patient_info'].copy()
                
                # 转换性别为中文
                gender_map = {'MALE': '男', 'FEMALE': '女', 'male': '男', 'female': '女'}
                if 'gender' in combined_patient_info:
                    combined_patient_info['gender'] = gender_map.get(
                        combined_patient_info['gender'], 
                        combined_patient_info['gender']
                    )
            else:
                avg_age = calculate_average_age(analysis_results)
                combined_patient_info = {
                    'name': f'{len(analysis_results)}个样本综合分析',
                    'gender': '综合',
                    'age': avg_age if avg_age > 0 else 35,
                    'id': 'COMBINED_ANALYSIS'
                }
            
            # 直接使用原有方法生成综合报告
            combined_html = generator.generate_report_from_algorithm(combined_result, combined_patient_info)
            
            if report_type == "combined":
                return combined_html
            else:
                generated_reports.append(combined_html)
                
        except Exception as e:
            raise ValueError(f"综合报告生成失败: {e}")
    
    # 返回结果
    if len(generated_reports) == 1:
        return generated_reports[0]
    else:
        return generated_reports
```

**说明：** 这个函数允许直接传递JSON数据生成报告，避免通过目录和文件系统的中间步骤。

## 调用方修改

### 1. algorithm_engine_manager.py

#### 修改内容：
1. **导入修改：**
   ```python
   # 原来
   from gemsage.multi_file_workflow import analyze_multiple_files, generate_reports_from_analyses
   
   # 修改为
   from gemsage.multi_file_workflow import analyze_multiple_files, generate_reports_from_analyses_json
   ```

2. **报告生成逻辑修改：**
   ```python
   # 原来的逻辑被替换为使用新方法
   report_html = generate_reports_from_analyses_json(analysis_results, "combined")
   ```

3. **文件名格式修改：**
   ```python
   # 修改为：名字_性别_年龄_当天日期
   report_filename = f"{patient_name}_{patient_gender}_{patient_age}岁_{today_date}.html"
   ```

4. **添加临时文件清理：**
   ```python
   # 清理不需要的JSON文件
   try:
       import shutil
       if os.path.exists(temp_analysis_dir):
           shutil.rmtree(temp_analysis_dir)
           logger.info(f"🗑️ 清理临时文件目录: {temp_analysis_dir}")
   except Exception as cleanup_error:
       logger.warning(f"清理临时文件失败: {cleanup_error}")
   ```

### 2. pressure_sensor_ui.py

#### 修改内容：
1. **PDF文件名格式修改：**
   ```python
   # 修改为：名字_性别_年龄_当天日期
   pdf_filename = f"{patient_name}_{patient_gender}_{patient_age}岁_{today_date}.pdf"
   ```

2. **报告数据获取路径修改：**
   ```python
   # 从 result['result'] 里获取报告数据
   result_data = result.get('result', {})
   report_html = result_data.get('report_html') or result.get('report_html')
   report_path = result_data.get('report_path') or result.get('report_path')
   ```

## 修改的原因和效果

### 问题：
1. 原有流程会生成多个重复的HTML和PDF文件
2. 通过文件系统读写JSON导致"数据不足"问题
3. 文件命名不规范，缺少患者信息

### 解决方案：
1. **直接数据传递：** 使用 `generate_reports_from_analyses_json` 直接传递内存中的分析结果
2. **统一文件命名：** HTML和PDF都使用 `名字_性别_年龄岁_日期` 格式
3. **清理临时文件：** 自动删除不需要的中间JSON文件
4. **避免重复生成：** 确保只生成一个HTML和一个PDF文件

### 最终效果：
- ✅ 只生成1个HTML文件（正确的综合分析报告）
- ✅ 只生成1个PDF文件（从HTML转换）
- ✅ 文件名包含患者基本信息
- ✅ 自动清理临时文件
- ✅ 避免"数据不足"问题

## 版本更新时的操作步骤

当 gemsage 模块更新时：

1. **备份当前修改：** 保存 `gemsage/multi_file_workflow.py` 的修改部分
2. **更新模块：** 安装新版本的 gemsage
3. **重新应用修改：** 
   - 将 `generate_reports_from_analyses_json` 函数添加到新版本的 `multi_file_workflow.py`
   - 确保导入语句正确
4. **测试功能：** 验证CSV导入和报告生成功能正常
5. **更新此文档：** 记录任何新的修改

## 注意事项

- 这些修改不会影响 gemsage 的原有功能
- 新增的函数是独立的，不会与原有代码冲突
- 如果 gemsage 更新后API发生变化，可能需要调整调用方的代码