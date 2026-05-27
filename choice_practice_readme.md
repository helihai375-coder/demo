# 选择题练习 Demo 使用说明

## 1. 准备 Word 题目

支持类似下面两种格式：

```text
72 應用實證醫學的方法，將有助於物理治療師提升在那些方面的臨床執業？
(A)僅療效、預後 (B)療效、預後、臨床經驗、篩檢與診斷測試
(C)僅療效、預後、篩檢與診斷測試 (D)僅療效
作答：____    标记：□不会 □不确定 □需复习
```

```text
[100-2 第 73 题]
73.下列實證醫學的步驟其先後順序為何？
A.①②③④
B.②①④③
C.①②④③
D.②①③④
作答：____    标记：□不会 □不确定 □需复习
```

## 2. 准备答案 CSV

格式参考 `answers_sample.csv`：

```csv
id,answer
72,B
73,B
76,C
```

## 3. 生成 JSON

把 Word 文件放到当前文件夹后运行：

```powershell
python word_to_questions_json.py questions.docx -a answers_sample.csv -o questions.json
```

## 4. 导入 HTML

打开 `choice_practice_demo.html`，点击页面顶部的“导入题库 JSON”，选择生成的 `questions.json`。
