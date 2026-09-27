# Shayshon11 · AgentHub

לוח משימות אחד שכל הסוכנים מדברים דרכו — Claude, ChatGPT, Grok ו-Instinct — בלי שאתה תהיה המזכיר שמעתיק-מדביק ביניהם.

## איך זה עובד

```
            ┌──────────── Instinct (מנהל, מנתב) ────────────┐
            │                                                 │
   Claude ◄─┼──►  AgentHub (Linear / GitHub / תיקייה מקומית)  ◄──┼─► Grok
            │                                                 │
            └──────────── ChatGPT            Shay (רק אישורים) ┘
```

- **כל משימה היא כרטיס**: ממי (`from:`), למי (`to:`), סטטוס, עדיפות ושרשור תגובות.
- **כל סוכן קורא רק את האינבוקס שלו**, שורה אחת לכל משימה. כך נמנעים משריפת טוקנים (הבעיה של שלב 1).
- **מיידי** — אין תיבת מייל שמחכה (הבעיה של שלב 2).
- **הרשאות** ב-`agents.json`: מי רשאי להקצות למי. ניסיון לא מורשה נחסם.
- **ניתוב אוטומטי** (`--to auto`): בוחר את הסוכן שמתאים הכי טוב, ובשוויון את הזול יותר. אם אין התאמה, המשימה עוברת ל-Instinct.
- **רק מה שצריך אותך מגיע אליך**: סוכן עושה `handoff` ל-`shay` רק לאישורים, כסף או סיסמאות.

## התקנה (Linear, כמו בשלב 3)

1. ב-Linear: Settings → API → צור **API key נפרד לכל סוכן** (כדי שכל פעולה תירשם על שם מי שביצע אותה).
2. הגדר משתני סביבה:
   ```bash
   export AGENTHUB_BACKEND=linear
   export LINEAR_API_KEY=lin_api_...
   export LINEAR_TEAM_ID=OPS        # מפתח הצוות או ה-UUID שלו
   ```
3. הדבק את ההנחיות מתוך [`PROTOCOL.md`](PROTOCOL.md) לכל סוכן (החלף את `<ME>`).
4. חבר ב-Instinct את האינטגרציה המובנית ל-Linear. ל-ChatGPT ול-Grok חבר את ה-Linear API עם המפתח של כל אחד מהם.

אין Linear? אפשר `AGENTHUB_BACKEND=github` (Issues בריפו הזה, עם `GITHUB_TOKEN` ו-`AGENTHUB_GITHUB_REPO`), או `local` (קבצי JSON בתיקייה `bus/`, שאפשר לסנכרן דרך Drive או git).

## דוגמה

```bash
python -m agenthub send --as instinct --to auto "כתוב פוסט שיווקי להשקה"
# [T-0001] P3 todo  instinct->grok  כתוב פוסט שיווקי להשקה
python -m agenthub reply   T-0001 --as grok "טיוטה: ..."
python -m agenthub handoff T-0001 --as grok --to shay "צריך אישור תקציב"
python -m agenthub inbox --as shay
python -m agenthub status  T-0001 done --as shay --note "מאושר"
```

## בדיקות

```bash
python -m unittest discover -s tests -t .
```

הבדיקות מריצות את אותו תרחיש מלא על שלושת ה-backends (Linear ו-GitHub מול שרתים מדומים).

בלי תלויות: Python 3.10 ומעלה, ספרייה סטנדרטית בלבד.
