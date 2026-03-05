# SpendWise Chat – Database Design (PostgreSQL)

## 1. Goals (מה ה-DB צריך לאפשר)

ה-Database צריך לתמוך ב-3 דברים עיקריים:

1) **Audit + Debug**  
   לשמור את ההודעה המקורית מ-WhatsApp (raw payload) כדי שנוכל:
   - להבין למה LLM טעה
   - לשחזר תקלות
   - להראות בראיון “אנחנו שומרים raw events”

2) **Data Integrity**  
   למנוע כפילויות (כי WhatsApp יכול לשלוח אותו event שוב), ולשמור קשרים נכונים בין:
   - user → messages → expenses

3) **Fast Analytics**  
   לשאול שאלות כמו:
   - כמה הוצאתי השבוע?
   - כמה הוצאנו על מסעדות החודש?
   - מי בזבז הכי הרבה?
   
   ולכן צריך:
   - אינדקסים נכונים
   - סכימה שמתאימה לאגרגציות SQL

---

## 2. Core Design Choices (החלטות סכימה)

### 2.1 PostgreSQL as Source of Truth
- כל החישובים (SUM/GROUP BY) נעשים ב-SQL.
- ה-LLM לא “מחשב” סכומים, רק מבין שפה ומייצר Structured Data.

### 2.2 Keep Raw Messages
- טבלת `messages` תשמור:
  - `raw_payload` JSONB (כל מה שבא מ-WhatsApp)
  - `text` שנחלץ (הטקסט עצמו)
  - `provider_message_id` (unique) כדי למנוע כפילויות

### 2.3 Group support בלי לסבך
- כל expense/message יכול להיות:
  - **Personal** (למשתמש יחיד)
  - **Group** (שייך לקבוצה)
- נעשה את זה עם `group_id` שהוא `NULL` עבור אישי.
- ככה אתם תומכים גם “משתמש יחיד” וגם “קבוצה” בלי לבנות 2 מערכות.

---

## 3. Tables (MVP)

> שמות עמודות מומלצים. אפשר לבחור UUID או BIGINT — בראיונות לרוב UUID נראה מודרני.

### 3.1 `users`
מייצג משתמש מזוהה לפי מספר טלפון (WhatsApp sender).

**Columns**
- `id` (UUID, PK)
- `phone_number` (TEXT, unique, not null) — לדוגמה `"97254xxxxxxx"`
- `display_name` (TEXT, null)
- `created_at` (TIMESTAMPTZ, not null, default now())

**Constraints**
- `UNIQUE(phone_number)`

**Indexes**
- Unique index על `phone_number` (מגיע אוטומטית עם UNIQUE)

---

### 3.2 `groups`
מייצג קבוצה (דירה / טיול / חברים). אופציונלי אבל מומלץ כבר עכשיו כי זה כמעט לא מוסיף מורכבות.

**Columns**
- `id` (UUID, PK)
- `name` (TEXT, not null)
- `created_by_user_id` (UUID, FK -> users.id, not null)
- `created_at` (TIMESTAMPTZ, not null, default now())

**Indexes**
- `INDEX(groups.created_by_user_id)`

---

### 3.3 `group_members`
חברות משתמשים בקבוצה.

**Columns**
- `group_id` (UUID, FK -> groups.id, not null)
- `user_id` (UUID, FK -> users.id, not null)
- `role` (TEXT, not null, default 'member') — ('member'/'admin') אפשר לעשות ENUM בהמשך
- `joined_at` (TIMESTAMPTZ, not null, default now())

**Primary Key**
- `PRIMARY KEY (group_id, user_id)`

**Indexes**
- `INDEX(group_members.user_id)` — למצוא קבוצות של משתמש

---

### 3.4 `messages`
כל הודעת WhatsApp שנכנסה (Raw event).

**Columns**
- `id` (UUID, PK)
- `provider` (TEXT, not null, default 'whatsapp') — מאפשר בעתיד Telegram וכו'
- `provider_message_id` (TEXT, not null) — message id של WhatsApp
- `user_id` (UUID, FK -> users.id, not null)
- `group_id` (UUID, FK -> groups.id, null) — NULL = אישי
- `text` (TEXT, null) — הטקסט שנחלץ מה-payload
- `raw_payload` (JSONB, not null)
- `received_at` (TIMESTAMPTZ, not null, default now())

**Constraints**
- `UNIQUE(provider, provider_message_id)`  
  (חשוב מאוד כדי למנוע כפילויות כש-WhatsApp עושה retries)

**Indexes**
- `INDEX(messages.user_id, received_at DESC)`
- `INDEX(messages.group_id, received_at DESC)` (אם group_id נפוץ)
- Optional: `GIN INDEX(messages.raw_payload)` אם תרצו חיפושים בתוך JSONB (לא חובה ב-MVP)

---

### 3.5 `expenses`
הוצאה מובנית שנחלצה מהודעה.

**Columns**
- `id` (UUID, PK)
- `user_id` (UUID, FK -> users.id, not null) — מי דיווח
- `group_id` (UUID, FK -> groups.id, null) — NULL = אישי
- `source_message_id` (UUID, FK -> messages.id, not null) — מאיזה הודעה זה הגיע
- `amount` (NUMERIC(12,2), not null)
- `currency` (TEXT, not null, default 'ILS')
- `merchant` (TEXT, null)
- `category` (TEXT, not null) — ב-MVP כ-Text. בהמשך אפשר ENUM
- `occurred_at` (TIMESTAMPTZ, not null) — הזמן של ההוצאה (ברירת מחדל: זמן ההודעה)
- `created_at` (TIMESTAMPTZ, not null, default now())

**Constraints**
- `amount > 0` (CHECK)
- `UNIQUE(source_message_id)`  
  (אם החלטתם: הודעה אחת מייצרת לכל היותר הוצאה אחת. זה מפשט מאוד את המערכת.)
  > אם בהמשך תרצו “הודעה שמכילה 2 הוצאות”, תורידו את זה ותעברו למודל one-to-many.

**Indexes (חשובים מאוד ל-Analytics)**
- `INDEX(expenses.user_id, occurred_at DESC)`
- `INDEX(expenses.group_id, occurred_at DESC)`
- `INDEX(expenses.category, occurred_at DESC)`
- Composite optional (ממש טוב):
  - `INDEX(expenses.user_id, category, occurred_at DESC)`
  - `INDEX(expenses.group_id, category, occurred_at DESC)`

---

## 4. LLM Metadata (Optional but recommended)

כדי להיראות “Senior”, אפשר לשמור metadata על הניתוח של ה-LLM.

### Option A – עמודות בתוך expenses (פשוט)
להוסיף:
- `llm_model` (TEXT, null)
- `llm_confidence` (NUMERIC(3,2), null) — 0.00–1.00
- `llm_raw_output` (JSONB, null)

### Option B – טבלה נפרדת `llm_runs` (יותר נקי)
אם רוצים Design יותר “Enterprise”:
- `llm_runs` עם:
  - prompt, response, latency_ms, tokens, error וכו’

ל-MVP: **Option A מספיק**.

---

## 5. Common Queries (איך הסכימה תומכת בשאלות)

### 5.1 Weekly summary (per user)
```sql
SELECT
  category,
  SUM(amount) AS total
FROM expenses
WHERE user_id = :user_id
  AND occurred_at >= date_trunc('week', now())
GROUP BY category
ORDER BY total DESC;
