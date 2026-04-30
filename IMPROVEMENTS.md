# خطة رفع نسب التطابق (Match Rate)

## المشكلة الأساسية

| التنبؤ (من LLM) | المتوقع (من المهندس) |
|-----------------|---------------------|
| Furnish and install all painting and wall finishes | PNT-01 (9'-6" High): Mfg: Sherwin Williams, Color: Wordly Gray #SW7043, Type: Eggshell |
| quantity: null | quantity: 14270.52 SF |

**السبب:** LLM يقرأ **Scope of Work** (نصوص عامة) بينما التقدير البشري يدمج بيانات من **Drawings** (أبعاد) + **Specifications** (ألوان، أنواع) + **Finish Schedules** (جداول)

---

## الحلول المقترحة (من الأسهل للأصعب)

### 1. ✅ تحسين الـ Prompt (سريع — 30 دقيقة)

**المشكلة:** الـ Prompt الحالي يطلب "وصف واضح" فقط

**الحل:** نطلب تفاصيل مشابهة للتقدير البشري:
- الرمز (PNT-01, CL-03)
- الشركة المصنعة
- اللون
- الارتفاع
- النوع (Eggshell, Glossy, Flat)

**مثال Prompt محسّن:**
```
Extract line items with DETAILED descriptions matching construction estimate format:
- Include product codes if found (e.g., PNT-01, CL-03)
- Include manufacturer (e.g., Sherwin Williams)
- Include color name and code (e.g., Wordly Gray #SW7043)
- Include height/elevation (e.g., 9'-6" High)
- Include finish type (e.g., Eggshell, Glossy)
- Include quantities in SF, LF, or EA

Example output format:
{
  "description": "PNT-01 (9'-6\" High): Mfg: Sherwin Williams, Color: Wordly Gray #SW7043, Type: Eggshell",
  "trade": "Painting",
  "quantity": 14270.52,
  "unit": "SF"
}
```

**التأثير المتوقع:** +15-25% match rate

---

### 2. ✅ Few-Shot Prompting (سريع — 1 ساعة)

**المشكلة:** LLM لا يعرف نمط التقدير البشري

**الحل:** نعطيه 3-5 أمثلة حقيقية من التقدير البشري كـ "examples"

**مثال:**
```
Here are examples of how line items should look:

Example 1:
Input: "Wall Paint - Eggshell finish, Wordly Gray"
Output: {"description": "PNT-01 (9'-6\" High): Mfg: Sherwin Williams, Color: Wordly Gray #SW7043, Type: Eggshell", "quantity": 14270.52, "unit": "SF"}

Example 2:
Input: "Ceiling paint flat white"
Output: {"description": "CL-03 (GWB): Mfg: Sherwin Williams, Color: Extra White #SW7006, Type: Flat", "quantity": 963.17, "unit": "SF"}

Now extract similar items from this content...
```

**التأثير المتوقع:** +20-30% match rate

---

### 3. ✅ تمرير جدول المواصفات (Specifications Table) كسياق (1-2 ساعة)

**المشكلة:** LLM لا يرى جدول الألوان والرموز

**الحل:** نستخرج جداول Finish Schedule من Specifications ونمررها كـ "context" للـ Prompt

**خطوات:**
1. نقرأ Specifications.pdf
2. نستخرج جداول الألوان (Color Schedule) والرموز
3. نضيفها للـ Prompt:
```
PROJECT FINISH SCHEDULE:
- PNT-01: Sherwin Williams, Wordly Gray #SW7043, Eggshell
- PNT-02: Sherwin Williams, Seasalt #SW6204, Eggshell
- CL-03: Sherwin Williams, Extra White #SW7006, Flat

Use these codes and details when describing paint items.
```

**التأثير المتوقع:** +25-35% match rate

---

### 4. ✅ Post-Processing: قاموس Mapping (2-3 ساعات)

**المشكلة:** حتى مع التحسينات، ستبقى فجوة

**الحل:** نبني قاموس يعيد تسمية الأوصاف العامة لأوصاف مطابقة

**مثال:**
```python
DESCRIPTION_MAPPING = {
    "painting and wall finishes": "PNT-01 (9'-6\" High): Mfg: Sherwin Williams, Color: Wordly Gray #SW7043, Type: Eggshell",
    "ceiling paint": "CL-03 (GWB): Mfg: Sherwin Williams, Color: Extra White #SW7006, Type: Flat",
    "drywall and finishing": "GWB-01: 5/8\" Type X Gypsum Wallboard",
}
```

**التأثير المتوقع:** +10-20% match rate

---

### 5. ⚠️ استخراج الكميات من الرسومات (صعب — 1-2 يوم)

**المشكلة:** الكميات null لأنها تأتي من الأبعاد في الرسومات

**الحل:**
1. قراءة جداول Room Finish Schedule من الرسومات
2. حساب مساحات الغرف من الأبعاد
3. تطبيق جدول المواد على المساحات

**مثال:**
```
Room Schedule:
- Room 101: 12' x 15' = 180 SF → PNT-01
- Room 102: 10' x 12' = 120 SF → PNT-02

Total PNT-01 = 180 + ... = 14,270.52 SF
```

**التأثير المتوقع:** +30-40% match rate (لكن يحتاج وقت طويل)

---

### 6. ⚠️ OCR للرسومات الممسوحة (صعب — 1-2 يوم)

**المشكلة:** ملفات الرسومات الممسوحة (scanned) تُرجع 0 items

**الحل:** تفعيل Tesseract OCR + تصحيح الصور (deskew, denoise)

**التأثير المتوقع:** +15-25% items إضافية

---

## الخطة العملية (الأسرع → الأبطأ)

| الخطوة | الوقت | التأثير | الأولوية |
|--------|-------|---------|----------|
| 1. تحسين Prompt | 30 دقيقة | +15-25% | ⭐⭐⭐ |
| 2. Few-Shot Examples | 1 ساعة | +20-30% | ⭐⭐⭐ |
| 3. تمرير Finish Schedule | 1-2 ساعة | +25-35% | ⭐⭐⭐ |
| 4. Post-Processing Mapping | 2-3 ساعات | +10-20% | ⭐⭐ |
| 5. استخراج الكميات من الرسومات | 1-2 يوم | +30-40% | ⭐ |
| 6. OCR للممسوحة | 1-2 يوم | +15-25% | ⭐ |

---

## التوقع الإجمالي

إذا طبقنا الخطوات 1-3 فقط:
- **الحالي:** 17-57% match
- **بعد التحسين:** 50-70% match

إذا طبقنا كل الخطوات:
- **الهدف:** 70-85% match

---

## هل نطبق الخطوات 1-3 الآن؟
