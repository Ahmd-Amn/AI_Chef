import json
import secrets
import math
from itertools import product

from flask import Blueprint, abort, redirect, render_template, request, session, url_for
from google import genai

planner = Blueprint('planner', __name__)

# Each recipe serves one. Nutrition values are approximate per serving.
MEALS = {
    'berry_oats': ('Blueberry oatmeal', '60 g oats, 100 g blueberries, 1 banana', 'Simmer oats in water until soft. Slice banana and fold in with blueberries.', (390, 10, 82, 5)),
    'apple_rice': ('Apple cinnamon rice', '75 g dry brown rice, 1 apple, cinnamon', 'Cook rice in water following packet timings. Dice apple and simmer with the rice and cinnamon until tender.', (370, 6, 81, 3)),
    'beans': ('Black bean rice bowl', '180 g cooked black beans, 150 g cooked brown rice, 1 tomato, 1 tsp olive oil', 'Dice tomato. Heat beans and rice until steaming throughout. Toss with tomato and oil.', (475, 20, 86, 7)),
    'lentils': ('Carrot lentil soup', '90 g dry red lentils, 2 carrots, 1 potato, 1 tsp olive oil', 'Dice vegetables. Rinse lentils. Simmer everything in water until vegetables and lentils are tender.', (540, 27, 94, 7)),
    'chickpeas': ('Roasted chickpea potatoes', '180 g cooked chickpeas, 250 g potato, 1 tsp olive oil, paprika', 'Cube potato. Toss with chickpeas, oil and paprika. Roast at 200°C until tender, turning halfway.', (535, 21, 91, 10)),
    'peas': ('Green pea pasta', '90 g dry wheat pasta, 150 g green peas, 1 tsp olive oil, lemon', 'Boil pasta following packet instructions. Cook peas until tender. Drain and toss with oil and lemon juice.', (500, 20, 86, 8)),
    'banana': ('Banana', '1 banana', 'Peel and serve.', (105, 1, 27, 0)),
    'apple': ('Fresh apple', '1 apple', 'Wash, core and slice.', (95, 0, 25, 0)),
}
SLOTS = {'Breakfast': ['berry_oats', 'apple_rice'], 'Lunch': ['beans', 'lentils', 'chickpeas', 'peas'],
         'Dinner': ['beans', 'lentils', 'chickpeas', 'peas'], 'Snack': ['apple', 'banana']}
ALIASES = {'gluten': ['wheat', 'oats'], 'wheat': ['wheat'], 'legume': ['beans', 'lentils', 'peas'],
           'pulse': ['beans', 'lentils', 'peas'], 'garbanzo': ['chickpeas'], 'gram': ['chickpeas']}


def eligible(slot, exclusions):
    words = [word.strip().casefold() for word in exclusions.split(',') if word.strip()]
    plurals = {'potatoes': 'potato', 'tomatoes': 'tomato', 
               'blueberries': 'blueberr', 'berries': 'berr'}
    words = [plurals.get(word, word.removesuffix('s')) for word in words]
    terms = [term for word in words for term in [word, *ALIASES.get(word, [])]]
    return [key for key in SLOTS[slot] if not any(term in ' '.join(MEALS[key][:3]).casefold()
                                                 for term in terms)]


def assemble_plan(choices, days, goal, calories=None):
    ids = []
    if calories is not None:
        for _ in range(days):
            meals = min(product(*choices.values()), key=lambda combo: (
                abs(sum(MEALS[key][3][0] for key in combo) - calories),
                sum(ids.count(key) for key in combo)))
            ids.extend(meals)
        return ids
    for _ in range(days):
        for options in choices.values():
            def rank(key):
                kcal, protein, _, _ = MEALS[key][3]
                preference = {'Maintain weight': 0, 'Muscle gain': -protein, 'Fat loss': kcal}[goal]
                return ids.count(key), preference
            ids.append(min(options, key=rank))
    return ids


@planner.route('/planner', methods=['GET', 'POST'])
def page():
    from flask import current_app
    db, query = current_app.extensions['planner_db']
    user = session.get('user_id')
    if not user:
        abort(401)
    draft = session.get('meal_draft')
    error = None
    settings = session.get('planner_settings', {})
    if request.method == 'POST':
        token = session.get('csrf_token')
        if not token or not secrets.compare_digest(token.encode(), request.form.get('token', '').encode()):
            abort(403)
        action = request.form.get('action')
        if action == 'generate':
            settings = request.form.to_dict()
            session['planner_settings'] = settings
            days = request.form.get('days')
            goal = request.form.get('goal')
            notes = request.form.get('preferences', '').strip()
            excluded = request.form.get('exclude', '').strip()
            if days not in ('1', '7') or goal not in ('Maintain weight', 'Fat loss', 'Muscle gain') or max(len(notes), len(excluded)) > 180:
                abort(400)
            try:
                calories = float(request.form['calories']) if request.form.get('calories', '').strip() else None
                current_weight = target_weight = None
                if goal == 'Fat loss':
                    current_weight = float(request.form.get('current_weight', ''))
                    target_weight = float(request.form.get('target_weight', ''))
                    if not all(math.isfinite(v) and 0 < v <= 1000 for v in (current_weight, target_weight)) or target_weight >= current_weight:
                        raise ValueError()
                if calories is not None and (not math.isfinite(calories) or not 0 < calories <= 10000):
                    raise ValueError()
            except ValueError:
                abort(400, description='Enter a positive daily calorie target and, for fat loss, positive weights with target below current weight.')
            slots = list(SLOTS) if 'snack' in request.form else list(SLOTS)[:3]
            choices = {slot: eligible(slot, excluded) for slot in slots}
            if not all(choices.values()):
                error = 'The recipe collection has too few matches for these exclusions.'
            else:
                ids = assemble_plan(choices, int(days), goal, calories)
                if notes:
                    prompt = ('Rank the supplied recipe IDs best first for these optional preferences. '
                              'Return a JSON array of IDs. ' +
                              json.dumps(dict(recipes={key: MEALS[key][:2] for options in choices.values()
                                                      for key in options}, preferences=notes)))
                    try:
                        with genai.Client(http_options={'timeout': 2500, 'retry_options': {'attempts': 1}}) as client:
                            reply = client.models.generate_content(model='gemini-3.8-flash', contents=prompt,
                                config={'response_mime_type': 'application/json', 'max_output_tokens': 256})
                        ranking = json.loads(reply.text)
                        if not isinstance(ranking, list) or not all(isinstance(key, str) for key in ranking):
                            raise ValueError()
                        for options in choices.values():
                            options.sort(key=lambda key: ranking.index(key) if key in ranking else len(ranking))
                        ids = assemble_plan(choices, int(days), goal, calories)
                    except Exception:
                        error = 'Your plan is ready. Extra preferences could not be applied this time.'
                draft = dict(ids=ids, slots=slots, exclude=excluded, goal=goal, calories=calories,
                             current_weight=current_weight, target_weight=target_weight, settings=settings)
        elif action == 'swap' and draft:
            index = request.form.get('index', type=int)
            if index is None or not 0 <= index < len(draft['ids']):
                abort(400)
            choices = eligible(draft['slots'][index % len(draft['slots'])], draft['exclude'])
            draft['ids'][index] = choices[(choices.index(draft['ids'][index]) + 1) % len(choices)]
            if len(choices) == 1:
                error = 'This is the only matching recipe for that meal.'
        elif action == 'save' and draft:
            query('INSERT INTO meal_plans(user_id, plan_json) VALUES (%s,%s)', (user, json.dumps(draft)))
            db().commit()
            draft = None
        elif action in ('open', 'delete'):
            params = (request.form.get('id', type=int), user)
            if action == 'delete':
                query('DELETE FROM meal_plans WHERE id=%s AND user_id=%s', params)
                db().commit()
            else:
                row = query('SELECT plan_json FROM meal_plans WHERE id=%s AND user_id=%s', params).fetchone()
                if not row:
                    abort(404)
                draft = json.loads(row['plan_json'])
                settings = draft.get('settings') or dict(
                    days=str(len(draft['ids']) // len(draft['slots'])), goal=draft['goal'],
                    exclude=draft.get('exclude', ''), calories=draft.get('calories') or '',
                    current_weight=draft.get('current_weight') or '', target_weight=draft.get('target_weight') or '',
                    snack='on' if 'Snack' in draft['slots'] else '')
                session['planner_settings'] = settings
        else:
            abort(400)
        session['meal_draft'] = draft
        if not error:
            return redirect(url_for('planner.page'), code=303)
    saved = query('SELECT id, created_at, plan_json FROM meal_plans WHERE user_id=%s ORDER BY id DESC', (user,)).fetchall()
    for row in saved:
        plan = json.loads(row['plan_json'])
        row['label'] = f"{plan['goal']} · {len(plan['ids']) // len(plan['slots'])} day(s) · {row['created_at']}"
    return render_template('planner.html', draft=draft, saved=saved, meals=MEALS, error=error, settings=settings)


@planner.errorhandler(400)
def invalid_plan(error):
    return render_template('planner.html', draft=session.get('meal_draft'), saved=[], meals=MEALS,
                           settings=request.form, error=error.description), 400
