from flask import request

SERVICE_ERROR = 'No services are available right now. Please try again later.'
AI_RATE_ERROR = 'AI usage limit reached. Please try again later.'
AI_ERROR = 'AI service temporarily unavailable; the system may be under maintenance. Please try again in about 1 minute. Recovery time is currently unknown.'


def form_errors():
    errors = {}
    data = request.form
    for key, limit in (('meal_name', 500), ('meal_portion', 200), ('exclude', 180), ('preferences', 180)):
        if len(data.get(key, '')) > limit:
            errors[key] = f'Use at most {limit} characters.'
    action = data.get('action')
    if action in ('estimate', 'save_custom') and not data.get('meal_name', '').strip():
        errors['meal_name'] = 'Enter at least one food or drink.'
    if action == 'save_custom' and not data.get('meal_portion', '').strip():
        errors['meal_portion'] = 'Enter the portions you reviewed.'
    if action == 'generate':
        if data.get('days') not in ('1', '7'):
            errors['days'] = 'Choose one day or seven days.'
        if data.get('goal') not in ('Maintain weight', 'Fat loss', 'Muscle gain'):
            errors['goal'] = 'Choose a goal.'
    import math
    numeric = {}
    if action == 'save_custom':
        numeric.update({key: (0, 10000, True) for key in ('kcal', 'protein_g', 'carbs_g', 'fat_g')})
    if action == 'generate':
        numeric['calories'] = (0, 10000, False)
        if data.get('goal') == 'Fat loss':
            numeric.update({key: (0, 1000, False) for key in ('current_weight', 'target_weight')})
    for key, (minimum, maximum, inclusive) in numeric.items():
        if key == 'calories' and not data.get(key, '').strip():
            continue
        try:
            value = float(data.get(key, ''))
            if not math.isfinite(value) or value > maximum or (value < minimum if inclusive else value <= minimum):
                raise ValueError()
        except ValueError:
            errors[key] = f'Enter a number {"from 0" if inclusive else "above 0"} up to {maximum}.'
    if data.get('goal') == 'Fat loss' and not any(key in errors for key in ('current_weight', 'target_weight')):
        if float(data.get('target_weight', 0)) >= float(data.get('current_weight', 0)):
            errors['target_weight'] = 'Enter a target below your current weight.'
    return errors
