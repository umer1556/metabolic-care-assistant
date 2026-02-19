# meal_bank.py
# Small curated set (expand later). carb_servings * 15g = rough carb estimate.

MEALS = [
    # Breakfast
    {"name": "Besan chilla + unsweetened yogurt", "slot": "breakfast", "tags": ["desi", "high_fiber", "low_satfat", "low_sodium"], "carb_servings": 2,
     "notes": "Add veggies. Keep oil minimal. Avoid sweetened yogurt."},
    {"name": "Veg omelette + 1 slice wholegrain toast", "slot": "breakfast", "tags": ["low_satfat", "low_sodium"], "carb_servings": 2,
     "notes": "Add tomato/capsicum/onion. Avoid extra butter."},
    {"name": "Oats porridge (unsweetened) + cinnamon", "slot": "breakfast", "tags": ["high_fiber", "low_satfat"], "carb_servings": 3,
     "notes": "Use milk/water as preferred. Avoid sugar; add nuts in small portion."},
    {"name": "Greek yogurt bowl + berries (small portion)", "slot": "breakfast", "tags": ["low_satfat", "low_sodium"], "carb_servings": 2,
     "notes": "Avoid honey/syrups. Add chia/flax if available."},

    # Lunch
    {"name": "Grilled chicken + salad + small brown rice", "slot": "lunch", "tags": ["low_satfat", "low_sodium"], "carb_servings": 3,
     "notes": "Keep rice portion small; add veg for volume."},
    {"name": "Chana salad bowl (chickpeas + veg + lemon)", "slot": "lunch", "tags": ["veg", "high_fiber", "low_satfat"], "carb_servings": 3,
     "notes": "Use lemon/spices instead of heavy sauces."},
    {"name": "Daal + salad + 1 medium roti", "slot": "lunch", "tags": ["desi", "high_fiber", "low_satfat"], "carb_servings": 3,
     "notes": "Avoid extra ghee; keep pickle minimal (salt)."},

    # Dinner
    {"name": "Baked fish + sautéed veg + small rice portion", "slot": "dinner", "tags": ["low_satfat", "low_sodium"], "carb_servings": 2,
     "notes": "Season with spices/lemon; keep salt low."},
    {"name": "Mixed veg curry (light oil) + 1 roti", "slot": "dinner", "tags": ["desi", "veg", "high_fiber"], "carb_servings": 3,
     "notes": "Control oil. Add salad. Keep roti medium."},
    {"name": "Chicken/veg soup + side salad", "slot": "dinner", "tags": ["low_satfat", "low_sodium"], "carb_servings": 1,
     "notes": "Watch salt in stock cubes; prefer homemade/low-sodium."},
    {"name": "Daal + mixed veg + 1 roti", "slot": "dinner", "tags": ["desi", "high_fiber", "low_satfat"], "carb_servings": 3,
     "notes": "Avoid extra ghee; add salad."},

    # Snacks
    {"name": "Fruit: apple OR guava (1 portion)", "slot": "snack", "tags": ["snack"], "carb_servings": 1,
     "notes": "Keep to one portion; avoid fruit juice."},
    {"name": "Nuts (small handful, unsalted)", "slot": "snack", "tags": ["snack", "low_sodium"], "carb_servings": 0,
     "notes": "Small portion. Avoid salted nuts."},
    {"name": "Cucumber + hummus (small)", "slot": "snack", "tags": ["snack", "low_satfat"], "carb_servings": 1,
     "notes": "Check hummus salt; keep portion small."},
]
