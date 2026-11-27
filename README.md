# AI Chef

AI Chef is a web application for finding recipes, following cooking instructions, planning meals, and tracking estimated nutrition. It helps home cooks turn available ingredients into meals and keep their cooking and food records in one place.

## What you can do

### Generate recipes from your ingredients

Enter the ingredients you have to receive an AI-generated recipe with an ingredient list and cooking instructions. Recipe generation is available without an account. For signed-in users, successful recipes are automatically saved to their personal history.

### Keep recipes and favorites

Browse previous recipes and mark favorites for later. History and Favorites open in a popup across the app, so users can explore saved recipes while staying on the meal planner or food tracker.

### Follow guided cooking steps

Cooking mode shows one instruction at a time, with Previous and Next controls and a timer that can be paused, resumed, or stopped. Step progress and timers continue when users return to the recipe while keeping the page open. Timer completion has a separate status announcement.

### Plan daily or weekly meals

Signed-in users can create a one-day or seven-day plan with breakfast, lunch, dinner, and an optional snack.

- Choose Maintain weight, Fat loss, or Muscle gain.
- Optionally enter a daily calorie target.
- Enter current and target weights when choosing Fat loss.
- Exclude ingredients and add cuisine, budget, or pantry preferences.
- Swap meals, review estimated daily nutrition, and save plans for later.

The planner selects from a small collection of plant-based recipes. Basic plans are assembled locally, while AI helps rank recipes for optional preferences. Calorie targets select the closest available menu. Ingredient exclusions use English-name matching and selected aliases.

### Track meals and estimated nutrition

Enter a meal such as “nasi putih, kari ayam, air milo,” with optional portion details. AI estimates calories, protein, carbohydrate, and fat, stating assumed portions for review.

Users can correct the portions and nutrition values before confirming a log, view daily and rolling seven-day totals, and delete entries. Food logs and saved meal plans belong to the signed-in account.

## How it works

AI Chef uses Python and Flask for its backend, Jinja templates for its pages, and JavaScript for recipe popups, guided cooking, and mobile navigation. Bootstrap, Tailwind CSS utilities, and shared custom styles support the interface.

Google Gemini generates recipes and meal nutrition estimates. TiDB, accessed through a MySQL-compatible connection, stores accounts, recipe history, favorites, meal plans, and food logs.

## Understanding the estimates

Nutrition values are estimates that depend on ingredients, preparation, and portion size. Users should review AI assumptions and check packaging or nutrition references where accuracy matters.

Meal suggestions require individual review for allergies, ingredient labels, and cross-contact risks. Medical dietary needs should be discussed with a qualified healthcare professional.
