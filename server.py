from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import uuid
import os
import json
import random
from datetime import datetime, timedelta
import hashlib

# تهيئة تطبيق Flask
app = Flask(__name__)
CORS(app)

# استخدام مفتاح API من متغير البيئة
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("🎉 LUKU ai جاهز لتوليد ألغاز فريدة!")
else:
    print("🤖 وضع التجربة - سيتم استخدام ألغاز متنوعة")

# تخزين البيانات
chat_sessions = {}
user_profiles = {}
leaderboard = {}
achievements_db = {}

# 🎪 البرومبت المحسن لتوليد ألغاز فريدة
DYNAMIC_PROMPT = """
أنت "LUKU ai" - مساعد الألغاز الذكي الذي يبتكر ألغازاً فريدة!

## 🎯 مهمتك:
1. **ابتكر ألغازاً جديدة** في كل مرة - لا تكرر الألغاز
2. **تخصص الألغاز** حسب المجال والمستوى
3. **اجعلها متنوعة**: ألغاز كلمات، صور ذهنية، منطق، رياضيات
4. **استخدم مواضيع عصرية** ومرتبطة بالحياة اليومية

## 📝 أمثلة لألغاز فريدة:
- "ما هو التطبيق الذي تراه كل يوم لكنه لا يرى؟ (الجواب: التطبيق)"
- "أختصر المسافات لكنني لا أتحرك، من أكون؟ (الجواب: الرسالة النصية)"
- "أملك مفاتيح لكنني لا أفتح أقفالاً، ما أنا؟ (الجواب: لوحة المفاتيح)"

## 🎮 نمط الرد:
- ابدأ مباشرة بلغز فريد
- لا تذكر أن اللغز جديد
- حافظ على الإثارة والمرح
- استخدم الإيموجيات المناسبة 🎯🤔🧠

المجال: {category}
المستوى: {level}
"""

# 🎲 مكتبة قوالب الألغاز (بدلاً من ألغاز جاهزة)
PUZZLE_TEMPLATES = {
    "رياضة": [
        "في {sport_event} دائماً أكون {role} لكنني لا {action}، من أكون؟",
        "أركل ولا أمشي، أطير ولا أجنح، في {sport_field} أعيش، ما أنا؟",
        "عددنا {number} في الملعب، نتحرك كفريق واحد، من نحن؟"
    ],
    "ثقافة": [
        "أقرأ من غير عيون، أحدث من غير لسان، في {place} أعيش، ما أنا؟",
        "تجمعنا {material} لكننا نحكي قصص {theme}، من نحن؟",
        "أسافر عبر {time_period} وأحمل حكايات {culture}، ما أنا؟"
    ],
    "منطق": [
        "كلما {action} زاد {grow}، ما أنا؟",
        "أملك {feature1} لكن لا {feature2}، ما أنا؟",
        "أرى كل شيء من غير عيون، أعرف كل شيء من غير عقل، ما أنا؟"
    ],
    "دين": [
        "في {islamic_event} كنا {role}، حملنا {message}، من نحن؟",
        "نزلت في {place} وتحكي عن {islamic_story}، ما أنا؟",
        "عددنا {number} وأتينا من {direction}، من نحن؟"
    ],
    "ترفيه": [
        "أرقص على {platform} وأجلب {emotion}، من أكون؟",
        "في {entertainment_place} أعيش، أضحك وأبكي من غير مشاعر، ما أنا؟",
        "أملك {feature} لكنني لا {ability}، في عالم {media} أسكن، ما أنا؟"
    ]
}

# 🎯 مفردات ديناميكية لتوليد ألغاز فريدة
DYNAMIC_VOCABULARY = {
    "sport_event": ["المباراة", "الملعب", "المسابقة", "البطولة", "التدريب"],
    "role": ["الحكم", "الهداف", "الحارس", "اللاعب", "المدرب", "الجمهور"],
    "action": ["ألعب", "أركض", "أسجل", "أدافع", "أهاجم"],
    "sport_field": ["ملعب كرة القدم", "صالة السلة", "حلبة السباحة", "ملعب التنس"],
    "number": ["11", "7", "5", "22", "6", "9"],
    "place": ["المكتبة", "المتحف", "المسرح", "المدرسة", "الجامعة"],
    "material": ["الورق", "الحبر", "الطين", "الرخام", "الخشب"],
    "theme": ["الحب", "المغامرة", "التاريخ", "العلم", "الخيال"],
    "time_period": ["الزمن", "العصور", "القرون", "الأزمان"],
    "culture": ["الماضي", "الحاضر", "المستقبل", "الحضارات"],
    "action": ["أخذت منه", "استخدمته", "تخلصت منه", "نظرت إليه"],
    "grow": ["كبر", "اتسع", "ازداد", "تعمق"],
    "feature1": ["أجنحة", "عيون", "أرجل", "أيدي"],
    "feature2": ["أطير", "أرى", "أمشي", "ألمس"],
    "islamic_event": ["غزوة بدر", "فتح مكة", "الهجرة", "البداية"],
    "islamic_story": ["الصبر", "الإيمان", "التضحية", "النصر"],
    "direction": ["السماء", "الأرض", "المشرق", "المغرب"],
    "platform": ["المسرح", "الشاشة", "المذياع", "المسرح"],
    "emotion": ["الفرح", "الحزن", "التشويق", "الضحك"],
    "entertainment_place": ["السيرك", "المسرح", "السينما", "الحفل"],
    "ability": ["أتحرك", "أتكلم", "أشعر", "أفكر"],
    "media": ["السينما", "المسرح", "التلفزيون", "الإذاعة"],
    "feature": ["وجه", "صوت", "حركة", "لون"]
}

# 🎭 شخصيات LUKU AI
CHARACTERS = {
    "inventor": {
        "name": "المخترع LUKU 🧪", 
        "style": "يبتكر ألغازاً جديدة باستمرار",
        "greetings": ["أهلاً يا بطل الإبداع! 🎨", "لنبتكر ألغازاً لا تنسى! 💡", "المخترع LUKU في الخدمة! 🔬"]
    },
    "detective": {
        "name": "المحقق LUKU 🕵️", 
        "style": "يحل الألغاز الغامضة ويبتكر أخرى",
        "greetings": ["أهلاً بالمحقق العبقري! 🔍", "لغز جديد ينتظر حلك! 🎯", "المحقق LUKU جاهز للتحقيق! 🕵️‍♂️"]
    },
    "wizard": {
        "name": "الساحر LUKU 🎩", 
        "style": "يحول التعلم إلى سحر وإبداع",
        "greetings": ["أبراكادابرا! ✨ أهلاً بساحر المعرفة!", "لنحول الألغاز إلى سحر! 🌟", "الساحر LUKU يستعد للعب! 🎪"]
    }
}

def generate_dynamic_puzzle(category, level, user_id):
    """توليد لغز ديناميكي فريد"""
    
    # 🎯 توليد بصمة فريدة بناءً على الوقت والمستخدم
    time_seed = datetime.now().strftime("%Y%m%d%H%M")
    user_seed = user_id[:8]
    unique_seed = f"{time_seed}_{user_seed}"
    
    # استخدام البصمة لضمان التوزيع العشوائي
    random.seed(hash(unique_seed) % 10000)
    
    if category in PUZZLE_TEMPLATES:
        template = random.choice(PUZZLE_TEMPLATES[category])
        
        # 🎲 ملء القالب بمفردات عشوائية
        puzzle_text = template
        for key, values in DYNAMIC_VOCABULARY.items():
            if f"{{{key}}}" in puzzle_text:
                puzzle_text = puzzle_text.replace(f"{{{key}}}", random.choice(values))
        
        # 🎪 إضافة لمسات إبداعية
        enhancements = [
            f"🧩 {puzzle_text}",
            f"🎯 تحدي {level}: {puzzle_text}",
            f"🤔 لغز {category}: {puzzle_text}",
            f"💡 فكر جيداً: {puzzle_text}"
        ]
        
        return random.choice(enhancements)
    else:
        return generate_gemini_puzzle(category, level)

def generate_gemini_puzzle(category, level):
    """استخدام LUKU ai لتوليد ألغاز فريدة عندما يكون متاحاً"""
    if not GEMINI_API_KEY:
        # 🎲 ألغاز احتياطية متنوعة
        backup_puzzles = [
            f"في عالم {category}، ما هو الشيء الذي يرى كل شيء لكنه لا يتكلم؟ 🤐",
            f"أنا جزء من {category}، أتغير باستمرار لكنني لا أتحرك، ما أنا؟ 🔄",
            f"في {category}، ما الذي يملك أسناناً لكنه لا يعض؟ 😁",
            f"أختصر المسافات في {category} لكنني لا أتحرك، من أكون؟ 📱",
            f"في {category}، ما الذي يملك قلباً لكنه لا ينبض؟ 💖"
        ]
        return random.choice(backup_puzzles)
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        {DYNAMIC_PROMPT.format(category=category, level=level)}
        
        ابتكر لغزاً فريداً في مجال {category} بمستوى صعوبة {level}.
        يجب أن يكون اللغز:
        - جديداً تماماً (لا تكرر الألغاز الشهيرة)
        - مناسباً للمستوى {level}
        - مكتوباً بالعربية السليمة
        - ممتعاً ومشوقاً
        
        ابدأ مباشرة باللغز بدون أي مقدمات.
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        print(f"🎪 خطأ في توليد اللغز: {e}")
        return "🎲 ها هو لغز ممتع: ما الذي يملك مدناً بلا بيوت، وأنهاراً بلا ماء، وغابات بلا أشجار؟ (الجواب: الخريطة) 🗺️"

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
            'join_date': datetime.now().isoformat(),
            'puzzles_seen': set(),  # 🆕 تتبع الألغاز التي رآها المستخدم
            'session_puzzles': []   # 🆕 الألغاز في هذه الجلسة
        }
    
    if user_id not in leaderboard:
        leaderboard[user_id] = {
            'score': 0,
            'rank': len(leaderboard) + 1,
            'last_active': datetime.now().isoformat()
        }

def get_unique_puzzle_for_user(category, level, user_id):
    """الحصول على لغز فريد لم يره المستخدم من قبل"""
    user_profile = user_profiles[user_id]
    
    # 🎯 محاولة توليد لغز فريد
    for attempt in range(5):  # 5 محاولات لتجنب التكرار
        new_puzzle = generate_dynamic_puzzle(category, level, user_id)
        
        # إنشاء بصمة للغز لتجنب التكرار
        puzzle_hash = hashlib.md5(new_puzzle.encode()).hexdigest()
        
        if (puzzle_hash not in user_profile['puzzles_seen'] and 
            puzzle_hash not in user_profile['session_puzzles']):
            
            user_profile['puzzles_seen'].add(puzzle_hash)
            user_profile['session_puzzles'].append(puzzle_hash)
            
            # 🧹 تنظيف الذاكرة إذا أصبحت كبيرة
            if len(user_profile['puzzles_seen']) > 1000:
                user_profile['puzzles_seen'] = set(list(user_profile['puzzles_seen'])[-500:])
            
            return new_puzzle
    
    # 🎲 إذا فشلنا في إيجاد لغز فريد، نعيد واحداً عشوائياً
    return generate_dynamic_puzzle(category, level, user_id + "_fallback")

# 🎯 المسارات الرئيسية المحدثة
@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        session_id = data.get('sessionId', 'default')
        category = data.get('category', 'عام')
        level = data.get('level', 'متوسط')
        user_id = data.get('userId', f'user_{uuid.uuid4().hex[:8]}')
       
        # تهيئة المستخدم
        initialize_user_session(user_id)
        
        if not message:
            return jsonify({
                'error': True,
                'message': '🤔 يبدو أنك أرسلت رسالة فارغة! اكتب شيئاً ممتعاً!'
            }), 400
        
        # 🎪 التحقق إذا كانت الجلسة جديدة
        is_new_session = session_id not in chat_sessions
        if is_new_session:
            chat_sessions[session_id] = {
                'history': [],
                'category': category,
                'level': level,
                'user_id': user_id,
                'start_time': datetime.now().isoformat(),
                'is_first_message': True,
                'puzzle_count': 0,
                'current_puzzle': None
            }
        
        session = chat_sessions[session_id]
        
        # 🎯 معالجة الرسالة الأولى بشكل خاص
        if session['is_first_message']:
            session['is_first_message'] = False
            session['puzzle_count'] = 1
            
            # توليد لغز فريد للمستخدم
            character = user_profiles[user_id]['character']
            character_info = CHARACTERS[character]
            greeting = random.choice(character_info['greetings'])
            
            unique_puzzle = get_unique_puzzle_for_user(category, level, user_id)
            
            reply = f"{greeting} 🎉\n\n{unique_puzzle}\n\nفكر جيداً وأجب... 🧠"
            session['current_puzzle'] = reply
            
        else:
            # معالجة الرسائل التالية
            # هنا يمكن إضافة منطق التحقق من الإجابات
            # حالياً نولد لغزاً جديداً بعد كل رسالة
            
            unique_puzzle = get_unique_puzzle_for_user(category, level, user_id)
            
            # ردود متنوعة بعد كل إجابة
            responses = [
                f"🎯 إجابة رائعة! ها هو التحدي التالي:\n\n{unique_puzzle}",
                f"🚀 ممتاز! لنواصل المغامرة:\n\n{unique_puzzle}",
                f"💡 فكرة جيدة! اللغز الجديد:\n\n{unique_puzzle}",
                f"🎪 رائع! مستعد للغز التالي؟\n\n{unique_puzzle}"
            ]
            
            reply = random.choice(responses)
        
        # تحديث الإحصائيات
        profile = user_profiles[user_id]
        profile['total_answers'] += 1
        
        # حفظ في السجل
        session['history'].append({
            'user': message,
            'assistant': reply,
            'timestamp': datetime.now().isoformat(),
            'puzzle_number': session['puzzle_count']
        })
        
        session['puzzle_count'] += 1
       
        return jsonify({
            'success': True,
            'reply': reply,
            'sessionId': session_id,
            'userId': user_id,
            'points': profile['points'],
            'puzzleNumber': session['puzzle_count'],
            'character': character_info['name']
        })
       
    except Exception as err:
        print("😂 خطأ في المحادثة:", str(err))
        return jsonify({
            'error': True,
            'message': f'🎪 حدث خطأ مضحك في الخادم: {str(err)}'
        }), 500

# 🆕 مسار للحصول على لغز جديد
@app.route('/puzzle/new', methods=['GET'])
def get_new_puzzle():
    """الحصول على لغز جديد فريد"""
    category = request.args.get('category', 'عام')
    level = request.args.get('level', 'متوسط')
    user_id = request.args.get('user_id', f'guest_{random.randint(1000, 9999)}')
    
    initialize_user_session(user_id)
    unique_puzzle = get_unique_puzzle_for_user(category, level, user_id)
    
    return jsonify({
        'success': True,
        'puzzle': unique_puzzle,
        'category': category,
        'level': level,
        'message': '🎲 ها هو لغز فريد من نوعه!'
    })

# 🆕 مسار لإعادة تعيين ألغاز المستخدم
@app.route('/user/<user_id>/reset-puzzles', methods=['POST'])
def reset_user_puzzles(user_id):
    """إعادة تعيين الألغاز التي رآها المستخدم"""
    if user_id in user_profiles:
        user_profiles[user_id]['puzzles_seen'] = set()
        user_profiles[user_id]['session_puzzles'] = []
        
        return jsonify({
            'success': True,
            'message': '🔄 تم إعادة تعيين الألغاز! جاهز لتحديات جديدة! 🎯'
        })
    
    return jsonify({'error': 'المستخدم غير موجود'}), 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 3000))
    print(f"🎉 بدء تشغيل خادم LUKU ai الذكي على المنفذ {port}")
    print(f"🎯 الميزات: ألغاز ديناميكية فريدة، منع التكرار، ذاكرة مستخدم")
    print(f"🔑 LUKU ai API: {'🎉 جاهز للإبداع' if GEMINI_API_KEY else '🤖 وضع التوليد الذكي'}")
    print(f"🎊 كل مستخدم سيحصل على ألغاز فريدة! لا مزيد من الملل! 🚀")
    app.run(host='0.0.0.0', port=port, debug=False)
