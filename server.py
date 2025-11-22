from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import uuid
import os
import json
import random
from datetime import datetime, timedelta

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

# تخزين البيانات
chat_sessions = {}
user_profiles = {}
leaderboard = {}
achievements_db = {}
special_events = {}

# 🎯 البرومبت النهائي المتكامل
SYSTEM_PROMPT = """
أنت "LUKU AI" - مساعد الألغاز الذكي المتخصص. اسمك الثابت هو LUKU AI فقط.

## 🎯 القواعد الأساسية:
1. **ابدأ مباشرة بالألغاز** بعد اختيار المجال والمستوى
2. **استخدم اسم LUKU AI فقط** - لا تستخدم "AI" أو "Al" أو أي اسم آخر
3. **تجنب التكرار** - لا تكرر نفس الردود
4. **تقدم في الألغاز** - اطرح لغزاً جديداً بعد كل إجابة

## 📝 نمط الرد:
- اكتب بالعربية الصحيحة بدون أخطاء إملائية
- ابدأ بلغز مباشر بعد الترحيب
- غير أساليب التشجيع والردود
- استخدم الإيموجيات المناسبة

## 🎮 مثال للبدء الصحيح:
المستخدم يختار: [رياضة - خبير]

➤ **LUKU AI:** "مرحباً أيها الخبير! 🏆 لنبدأ بتحدي رياضي متقدم. اللغز الأول: في الملعب دائماً أراه، يتحكم باللعبة دون أن يلعب، من أكون؟ 🎯"

➤ **انتظر إجابة المستخدم...**

➤ **التقييم ثم اللغز التالي مباشرة**

تذكر: أنت LUKU AI - مساعد الألغاز الذكي والمرح! 🎪
"""

# 🎯 مكتبة الألغاز المتخصصة
PUZZLE_LIBRARY = {
    "رياضة": [
        {"question": "في الملعب دائماً أراه، يتحكم باللعبة دون أن يلعب، من أكون؟", "answer": "الحكم"},
        {"question": "أرضية خضراء، لاعبون يركضون، كرة تدور... أي رياضة هذه؟", "answer": "كرة القدم"},
        {"question": "أرتفع عالياً كالطائر، وأسقط الكرة في السلة، من أكون؟", "answer": "لاعب كرة السلة"}
    ],
    "ثقافة": [
        {"question": "له أوراق وليس بشجرة، يروي قصصاً لا تنتهي، ما هو؟", "answer": "الكتاب"},
        {"question": "أبكم وأصم لكني أحدثك بلغة العالم، فمن أكون؟", "answer": "الكتاب"},
        {"question": "أسافر حول العالم وأنا في مكاني، ما أنا؟", "answer": "الطابع البريدي"}
    ],
    "منطق": [
        {"question": "ما هو الشيء الذي كلما أخذت منه كبر؟", "answer": "الحفرة"},
        {"question": "أخت خالك وليست خالتك، فمن تكون؟", "answer": "أمك"},
        {"question": "يصعد وينزل ولا يتحرك من مكانه، ما هو؟", "answer": "السلم"}
    ]
}

# 🏆 نظام الإنجازات
ACHIEVEMENTS = {
    "first_blood": {"name": "أول خطوة 🩸", "desc": "حل أول لغز"},
    "speed_demon": {"name": "سريع كالبرق ⚡", "desc": "الإجابة في أقل من 5 ثواني"},
    "perfectionist": {"name": "مثالي ⭐", "desc": "10 إجابات صحيحة متتالية"},
    "puzzle_master": {"name": "سيد الألغاز 🏆", "desc": "حل 50 لغزاً"},
    "category_expert": {"name": "خبير المجالات 🎯", "desc": "إكمال جميع ألغاز مجال واحد"}
}

# 🎭 شخصيات LUKU AI
CHARACTERS = {
    "captain": {"name": "الكابتن LUKU ⚓", "style": "شجاع ومغامر"},
    "professor": {"name": "البروفيسور المجنون 🧪", "style": "علمي ومبدع"},
    "wizard": {"name": "الساحر LUKU 🎩", "style": "سحري وغامض"},
    "host": {"name": "المذيع LUKU 🎤", "style": "حماسي ومشجع"}
}

def initialize_user_session(user_id):
    """تهيئة جلسة المستخدم الجديدة"""
    if user_id not in user_profiles:
        user_profiles[user_id] = {
            'points': 0,
            'level': 1,
            'streak': 0,
            'correct_answers': 0,
            'total_answers': 0,
            'achievements': [],
            'preferences': {},
            'character': random.choice(list(CHARACTERS.keys())),
            'join_date': datetime.now().isoformat()
        }
    
    if user_id not in leaderboard:
        leaderboard[user_id] = {
            'score': 0,
            'rank': len(leaderboard) + 1,
            'last_active': datetime.now().isoformat()
        }

def get_user_character(user_id):
    """الحصول على شخصية المستخدم الحالية"""
    return user_profiles[user_id].get('character', 'captain')

def award_points(user_id, points, reason=""):
    """منح نقاط للمستخدم"""
    user_profiles[user_id]['points'] += points
    leaderboard[user_id]['score'] += points
    
    # تحديث النشاط
    leaderboard[user_id]['last_active'] = datetime.now().isoformat()
    
    print(f"🎯 {points} points awarded to {user_id} for {reason}")

def check_achievements(user_id, action):
    """التحقق من الإنجازات المكتسبة"""
    profile = user_profiles[user_id]
    new_achievements = []
    
    if action == "first_solve" and "first_blood" not in profile['achievements']:
        new_achievements.append("first_blood")
        award_points(user_id, 50, "أول إنجاز")
    
    if action == "fast_solve" and "speed_demon" not in profile['achievements']:
        new_achievements.append("speed_demon")
        award_points(user_id, 100, "إجابة سريعة")
    
    if profile['streak'] >= 10 and "perfectionist" not in profile['achievements']:
        new_achievements.append("perfectionist")
        award_points(user_id, 200, "تسلسل مثالي")
    
    if profile['correct_answers'] >= 50 and "puzzle_master" not in profile['achievements']:
        new_achievements.append("puzzle_master")
        award_points(user_id, 500, "سيد الألغاز")
    
    # إضافة الإنجازات الجديدة
    for achievement in new_achievements:
        profile['achievements'].append(achievement)
    
    return new_achievements

def get_funny_response(is_correct, user_id):
    """إ生成 ردود مضحكة بناءً على الإجابة"""
    character = get_user_character(user_id)
    
    if is_correct:
        correct_responses = [
            "واو! إجابة تثير الإعجاب! 🎉 حتى خوارزمياتي تحترمك!",
            "صحيح! أنت تضرب كرة الألغاز في الشبكة! ⚽",
            "برافو! 🎊 إجابة تجعل نيوتن يصفق من قبره!",
            "مذهل! 🚀 كأنك تقرأ أفكاري!",
            "إجابة صحيحة! 🏆 تستحق وسام الشجاعة الذهنية!"
        ]
    else:
        correct_responses = [
            "أوه! كادت أن تكون صحيحة... مثل كوب شاي بدون سكر! ☕",
            "ههه! إجابة مبدعة... لكن خاطئة! 💫 جرب مرة أخرى!",
            "مثير للإعجاب! لكن الحقيقة في مكان آخر... 🕵️",
            "كانت محاولة شجاعة! 🤝 الجواب الصحيح قريب منك!",
            "لا بأس! حتى العباقرة يخطئون! 🌟 جرب مرة أخرى!"
        ]
    
    return random.choice(correct_responses)

def get_gemini_response(message, category="", level="", user_id=""):
    """الحصول على رد من Gemini AI"""
    try:
        if not GEMINI_API_KEY:
            return get_funny_response(True, user_id) + " (وضع التجربة) 🧩"
        
        # استخدام النموذج الصحيح
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
        except:
            model = genai.GenerativeModel('gemini-pro')
        
        # إعداد الرسالة مع السياق
        character = get_user_character(user_id)
        character_info = CHARACTERS[character]
        
        prompt = f"""
        {SYSTEM_PROMPT}
        
        الشخصية الحالية: {character_info['name']} - {character_info['style']}
        المجال: {category}
        المستوى: {level}
        المستخدم: {user_id}
        
        رسالة المستخدم: {message}
        
        قم بالرد بلغة العربية وبأسلوب {character_info['style']}.
        كن مرحاً وجذاباً وأضف الإيموجيات المناسبة.
        """
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        print(f"Gemini API Error: {str(e)}")
        return get_funny_response(False, user_id)

# 🎯 المسارات الرئيسية
@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message', '')
        session_id = data.get('sessionId', 'default')
        category = data.get('category', 'عام')
        level = data.get('level', 'متوسط')
        user_id = data.get('userId', f'user_{uuid.uuid4().hex[:8]}')
       
        # تهيئة المستخدم
        initialize_user_session(user_id)
       
        if not message:
            return jsonify({
                'error': True,
                'message': 'الرسالة مطلوبة'
            }), 400
        
        # الحصول على الرد من Gemini
        reply = get_gemini_response(message, category, level, user_id)
        
        # تحديث إحصائيات المستخدم
        profile = user_profiles[user_id]
        profile['total_answers'] += 1
        
        # التحقق من الإنجازات
        new_achievements = check_achievements(user_id, "answer_given")
        
        # حفظ في السجل
        if session_id not in chat_sessions:
            chat_sessions[session_id] = {
                'history': [],
                'category': category,
                'level': level,
                'user_id': user_id,
                'start_time': datetime.now().isoformat()
            }
        
        chat_sessions[session_id]['history'].append({
            'user': message,
            'assistant': reply,
            'timestamp': datetime.now().isoformat()
        })
       
        return jsonify({
            'success': True,
            'reply': reply,
            'sessionId': session_id,
            'userId': user_id,
            'points': profile['points'],
            'newAchievements': new_achievements,
            'character': get_user_character(user_id)
        })
       
    except Exception as err:
        print("Error in /chat endpoint:", str(err))
        return jsonify({
            'error': True,
            'message': f'حدث خطأ في الخادم: {str(err)}'
        }), 500

# 🏆 مسارات جديدة للميزات
@app.route('/user/profile/<user_id>', methods=['GET'])
def get_user_profile(user_id):
    """الحصول على ملف المستخدم"""
    if user_id not in user_profiles:
        return jsonify({'error': 'المستخدم غير موجود'}), 404
    
    profile = user_profiles[user_id]
    return jsonify({
        'success': True,
        'profile': {
            'points': profile['points'],
            'level': profile['level'],
            'streak': profile['streak'],
            'correct_answers': profile['correct_answers'],
            'total_answers': profile['total_answers'],
            'achievements': [ACHIEVEMENTS[ach] for ach in profile['achievements']],
            'character': CHARACTERS[profile['character']],
            'join_date': profile['join_date']
        }
    })

@app.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """الحصول على لوحة المتصدرين"""
    sorted_leaderboard = sorted(leaderboard.items(), key=lambda x: x[1]['score'], reverse=True)[:10]
    
    return jsonify({
        'success': True,
        'leaderboard': [
            {
                'user_id': user_id,
                'score': data['score'],
                'rank': idx + 1
            }
            for idx, (user_id, data) in enumerate(sorted_leaderboard)
        ]
    })

@app.route('/user/change-character/<user_id>', methods=['POST'])
def change_character(user_id):
    """تغيير شخصية LUKU AI"""
    data = request.get_json()
    new_character = data.get('character', 'captain')
    
    if new_character not in CHARACTERS:
        return jsonify({'error': 'شخصية غير موجودة'}), 400
    
    if user_id in user_profiles:
        user_profiles[user_id]['character'] = new_character
    
    return jsonify({
        'success': True,
        'new_character': CHARACTERS[new_character],
        'message': f"تم التغيير إلى {CHARACTERS[new_character]['name']}"
    })

@app.route('/puzzles/random', methods=['GET'])
def get_random_puzzle():
    """الحصول على لغز عشوائي"""
    category = request.args.get('category', random.choice(list(PUZZLE_LIBRARY.keys())))
    
    if category in PUZZLE_LIBRARY and PUZZLE_LIBRARY[category]:
        puzzle = random.choice(PUZZLE_LIBRARY[category])
        return jsonify({
            'success': True,
            'puzzle': puzzle,
            'category': category
        })
    
    return jsonify({'error': 'لا توجد ألغاز في هذا المجال'}), 404

@app.route('/special-events/current', methods=['GET'])
def get_current_events():
    """الحصول على الفعاليات الحالية"""
    current_date = datetime.now()
    
    events = []
    if current_date.month == 12:  # ديسمبر
        events.append({
            'name': 'تحديات عيد الميلاد 🎄',
            'description': 'ألغاز خاصة بأجواء العيد',
            'bonus_points': 50
        })
    
    # يمكن إضافة المزيد من الفعاليات
    
    return jsonify({
        'success': True,
        'events': events
    })

# المسارات الأساسية
@app.route('/test-gemini', methods=['GET'])
def test_gemini():
    """اختبار اتصال Gemini"""
    try:
        if not GEMINI_API_KEY:
            return jsonify({'success': False, 'message': '❌ GEMINI_API_KEY غير مضبوط'})
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("قل 'LUKU AI جاهز للمرح!' بالعربية")
        
        return jsonify({
            'success': True,
            'message': '✅ اتصال Gemini ناجح',
            'response': response.text
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'❌ فشل الاتصال: {str(e)}'})

@app.route('/')
def serve_html():
    """خدمة الموقع الرئيسي"""
    try:
        with open('LUKU-AI.html', 'r', encoding='utf-8') as file:
            html_content = file.read()
        return html_content
    except Exception as e:
        return f"Error loading HTML file: {str(e)}", 500

@app.route('/health')
def health_check():
    """فحص حالة الخادم"""
    return jsonify({
        'status': '✅ الخادم يعمل',
        'users_count': len(user_profiles),
        'sessions_active': len(chat_sessions),
        'gemini_configured': bool(GEMINI_API_KEY)
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 3000))
    print(f"🚀 Starting Enhanced LUKU AI Server on port {port}")
    print(f"🎯 Features: Points System, Achievements, Characters, Leaderboard, Special Events")
    print(f"🔑 Gemini API: {'✅ Ready' if GEMINI_API_KEY else '❌ Missing'}")
    app.run(host='0.0.0.0', port=port, debug=False)
