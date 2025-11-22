from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import uuid
import os

# تهيئة تطبيق Flask
app = Flask(__name__)
CORS(app)  # تمكين CORS

# استخدام مفتاح API من متغير البيئة
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("✅ Gemini API configured successfully")
else:
    print("❌ GEMINI_API_KEY not found")

# تخزين المحادثات
chat_sessions = {}

# prompt النظام
SYSTEM_PROMPT = """أنت مساعد باسم "LUKU AI"، مختص بالكامل في الألعاب، الألغاز، الأسئلة المنطقية.
إذا سُئلت عن شيء خارج هذا المجال، اكتب: "عذرًا أنا مساعد LUKU AI مختص في الألعاب والألغاز فقط."
كن مرحًا وابتكر ألغاز وأسئلة ذكاء ممتعة، استخدم الإيموجيات بشكل مناسب.
قدم الألغاز بناءً على المجال ومستوى الصعوبة المحدد."""

def get_gemini_response(message, category="", level=""):
    """الحصول على رد من Gemini AI"""
    try:
        if not GEMINI_API_KEY:
            return "❌ خطأ: مفتاح API غير مضبوط. يرجى إضافة GEMINI_API_KEY في إعدادات Railway."
        
        # إنشاء النموذج
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # إعداد الرسالة مع التعليمات
        full_message = f"""
        {SYSTEM_PROMPT}
        
        المجال: {category}
        مستوى الصعوبة: {level}
        
        رسالة المستخدم: {message}
        
        قم بالرد بلغة العربية وبشكل مرح وجذاب مع الإيموجيات المناسبة:
        """
        
        # إرسال الرسالة
        response = model.generate_content(full_message)
        return response.text
        
    except Exception as e:
        print(f"Gemini API Error: {str(e)}")
        return f"🧩 عذرًا، حدث خطأ في خدمة الألغاز: {str(e)}. جرب مرة أخرى لاحقًا!"

# مسار للدردشة
@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message', '')
        session_id = data.get('sessionId', 'default')
        category = data.get('category', 'عام')
        level = data.get('level', 'متوسط')
       
        if not message:
            return jsonify({
                'error': True,
                'message': 'الرسالة مطلوبة'
            }), 400
        
        # الحصول على الرد من Gemini
        reply = get_gemini_response(message, category, level)
        
        # حفظ في السجل
        if session_id not in chat_sessions:
            chat_sessions[session_id] = {
                'history': [],
                'category': category,
                'level': level
            }
        
        chat_sessions[session_id]['history'].append({
            'user': message,
            'assistant': reply
        })
       
        return jsonify({
            'success': True,
            'reply': reply,
            'sessionId': session_id
        })
       
    except Exception as err:
        print("Error in /chat endpoint:", str(err))
        return jsonify({
            'error': True,
            'message': f'حدث خطأ في الخادم: {str(err)}'
        }), 500

# مسار لاختبار الاتصال بـ Gemini
@app.route('/test-gemini', methods=['GET'])
def test_gemini():
    """لاختبار اتصال Gemini AI"""
    try:
        if not GEMINI_API_KEY:
            return jsonify({
                'success': False,
                'message': '❌ GEMINI_API_KEY غير مضبوط'
            })
        
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("قل 'مرحبًا من LUKU AI' بالعربية فقط بدون أي شرح إضافي")
        
        return jsonify({
            'success': True,
            'message': '✅ اتصال Gemini ناجح',
            'response': response.text,
            'api_key_exists': bool(GEMINI_API_KEY)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'❌ فشل اتصال Gemini: {str(e)}',
            'api_key_exists': bool(GEMINI_API_KEY)
        })

# مسار رئيسي لخدمة الموقع
@app.route('/')
def serve_html():
    try:
        with open('LUKU-AI.html', 'r', encoding='utf-8') as file:
            html_content = file.read()
        return html_content
    except Exception as e:
        return f"Error loading HTML file: {str(e)}", 500

# مسار لفحص حالة الخادم
@app.route('/health')
def health_check():
    return jsonify({
        'status': '✅ الخادم يعمل',
        'gemini_configured': bool(GEMINI_API_KEY),
        'sessions_active': len(chat_sessions)
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 3000))
    print(f"🚀 Starting LUKU AI Server on port {port}")
    print(f"🔑 Gemini API Key: {'✅ Found' if GEMINI_API_KEY else '❌ Missing'}")
    app.run(host='0.0.0.0', port=port, debug=False)
