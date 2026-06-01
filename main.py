# 导入FastAPI核心类
from fastapi import FastAPI, File, UploadFile
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request
import os
import uuid
import pdfplumber
import requests
import json
from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL

# 创建FastAPI应用实例
app = FastAPI(title="AI Job Assistant", version="1.0")

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 初始化模板引擎
templates = Jinja2Templates(directory="templates")

# 定义上传文件保存目录
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# ==================== 公共请求头 ====================
def get_headers():
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

# ==================== 首页 ====================
@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# ==================== 文件上传 ====================
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        if file.content_type != "application/pdf":
            return {"success": False, "message": "只能上传PDF格式的文件！"}
        
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        return {
            "success": True,
            "saved_filename": unique_filename
        }
    except Exception as e:
        return {"success": False, "message": f"上传失败：{str(e)}"}

# ==================== PDF解析 ====================
@app.post("/api/parse")
async def parse_pdf(request: Request):
    try:
        data = await request.json()
        saved_filename = data.get("saved_filename")
        if not saved_filename:
            return {"success": False, "message": "缺少文件名参数！"}
        
        file_path = os.path.join(UPLOAD_DIR, saved_filename)
        if not os.path.exists(file_path):
            return {"success": False, "message": "文件不存在！"}
        
        with pdfplumber.open(file_path) as pdf:
            text_content = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n\n"
        
        return {"success": True, "content": text_content}
    except Exception as e:
        return {"success": False, "message": f"解析失败：{str(e)}"}

# ==================== AI简历评分 ====================
@app.post("/api/analyze")
async def analyze_resume(request: Request):
    try:
        data = await request.json()
        resume_content = data.get("resume_content")
        if not resume_content:
            return {"success": False, "message": "缺少简历内容！"}
        
        prompt = f"""
请你作为专业HR，分析以下简历，严格返回JSON格式，无其他文字：
{{
    "overall_score": 0-100,
    "skill_score": 0-100,
    "project_score": 0-100,
    "competitiveness_score": 0-100,
    "advantages": ["优点1","优点2","优点3"],
    "disadvantages": ["缺点1","缺点2","缺点3"],
    "suggestions": ["建议1","建议2","建议3"]
}}
简历：{resume_content}
"""
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "response_format": {"type": "json_object"}
        }
        res = requests.post(DEEPSEEK_API_URL, headers=get_headers(), json=payload)
        res.raise_for_status()
        analysis_result = json.loads(res.json()["choices"][0]["message"]["content"])
        return {"success": True, "analysis": analysis_result}
    except Exception as e:
        return {"success": False, "message": f"分析失败：{str(e)}"}

# ==================== AI智能岗位推荐（无固定数据） ====================
@app.post("/api/recommend")
async def recommend_jobs(request: Request):
    try:
        data = await request.json()
        resume_content = data.get("resume_content")
        if not resume_content:
            return {"success": False, "message": "缺少简历内容！"}

        prompt = f"""
你是顶级职业规划师，根据简历内容，自动生成3个最适合的岗位。
严格返回JSON，禁止多余文字！
{{
    "jobs": [
        {{
            "title": "岗位名称",
            "company": "知名企业",
            "location": "工作城市",
            "salary": "薪资区间",
            "similarity_score": 匹配度0-100,
            "match_analysis": {{
                "match_level": "高/中/低",
                "matched_skills": ["已掌握技能"],
                "missing_skills": ["欠缺技能"],
                "improvement_suggestions": ["学习提升建议"]
            }}
        }}
    ]
}}
简历内容：{resume_content}
"""
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
            "response_format": {"type": "json_object"}
        }
        res = requests.post(DEEPSEEK_API_URL, headers=get_headers(), json=payload)
        res.raise_for_status()
        result = json.loads(res.json()["choices"][0]["message"]["content"])
        return {"success": True, "jobs": result["jobs"]}
    except Exception as e:
        return {"success": False, "message": f"岗位推荐失败：{str(e)}"}

# ==================== 新增：AI生成岗位面试题接口 ====================
@app.post("/api/interview")
async def gen_interview_question(request: Request):
    try:
        data = await request.json()
        resume_content = data.get("resume_content")
        job_title = data.get("job_title")
        if not resume_content or not job_title:
            return {"success": False, "message": "缺少简历或岗位名称！"}

        prompt = f"""
请结合求职者简历水平，生成【{job_title}】真实职场面试题，贴合应届生/职场新人难度，
分为三类题型，每题附带标准回答，严格返回JSON格式，不要多余内容：

{{
    "job_name":"对应岗位",
    "base_questions":[
        {{"question":"基础问题","answer":"标准回答"}}
    ],
    "senior_questions":[
        {{"question":"进阶问题","answer":"标准回答"}}
    ],
    "project_questions":[
        {{"question":"项目场景题","answer":"答题思路+答案"}}
    ]
}}

求职者简历：{resume_content}
要求：基础题5道，进阶题4道，项目场景题3道
"""
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.6,
            "response_format": {"type": "json_object"}
        }
        res = requests.post(DEEPSEEK_API_URL, headers=get_headers(), json=payload)
        res.raise_for_status()
        interview_data = json.loads(res.json()["choices"][0]["message"]["content"])
        return {"success": True, "interview": interview_data}
    except Exception as e:
        return {"success": False, "message": f"面试题生成失败：{str(e)}"}