from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.models.models import db, DrugClass, Drug
import math
from datetime import datetime, date

pharma_bp = Blueprint('pharma', __name__)

@pharma_bp.route('/')
@login_required
def index():
    # Get all drug classes
    drug_classes = DrugClass.query.order_by(DrugClass.name).all()
    
    # Get recently added drugs
    recent_drugs = Drug.query.order_by(Drug.created_at.desc()).limit(6).all()
    
    # Get popular calculators
    calculators = [
        {
            'name': 'Dose Calculator',
            'description': 'Calculate medication dosages based on patient weight and prescribed dose',
            'url': url_for('pharma.dose_calculator'),
            'icon': 'fas fa-pills',
            'color': '#1a6ac3'
        },
        {
            'name': 'IV Drip Rate Calculator',
            'description': 'Calculate IV infusion rates and drip rates',
            'url': url_for('pharma.drip_calculator'),
            'icon': 'fas fa-tint',
            'color': '#213874'
        },
        {
            'name': 'BMI Calculator',
            'description': 'Calculate Body Mass Index for medication dosing',
            'url': url_for('pharma.bmi_calculator'),
            'icon': 'fas fa-weight',
            'color': '#f3ab1b'
        },
        {
            'name': 'Creatinine Clearance',
            'description': 'Estimate kidney function for drug dosing adjustments',
            'url': url_for('pharma.creatinine_calculator'),
            'icon': 'fas fa-kidney',
            'color': '#1a6ac3'
        },
        {
            'name': 'Pregnancy Due Date',
            'description': 'Calculate expected delivery date for pregnancy medications',
            'url': url_for('pharma.pregnancy_calculator'),
            'icon': 'fas fa-baby',
            'color': '#213874'
        },
        {
            'name': 'Unit Converter',
            'description': 'Convert between different pharmaceutical units',
            'url': url_for('pharma.unit_converter'),
            'icon': 'fas fa-exchange-alt',
            'color': '#f3ab1b'
        }
    ]
    
    return render_template('pharmacology/index.html',
                         drug_classes=drug_classes,
                         recent_drugs=recent_drugs,
                         calculators=calculators)

@pharma_bp.route('/drug-classes')
@login_required
def drug_classes():
    search = request.args.get('search', '')
    
    query = DrugClass.query
    
    if search:
        query = query.filter(
            db.or_(
                DrugClass.name.contains(search),
                DrugClass.description.contains(search)
            )
        )
    
    drug_classes = query.order_by(DrugClass.name).all()
    
    return render_template('pharmacology/drug_classes.html',
                         drug_classes=drug_classes,
                         search=search)

@pharma_bp.route('/drug-class/<int:class_id>')
@login_required
def drug_class_detail(class_id):
    drug_class = DrugClass.query.get_or_404(class_id)
    drugs = Drug.query.filter_by(drug_class_id=class_id).order_by(Drug.name).all()
    
    return render_template('pharmacology/drug_class_detail.html',
                         drug_class=drug_class,
                         drugs=drugs)

@pharma_bp.route('/drug/<int:drug_id>')
@login_required
def drug_detail(drug_id):
    drug = Drug.query.get_or_404(drug_id)
    
    # Parse JSON fields
    import json
    brand_names = []
    dosage_forms = []
    
    try:
        if drug.brand_names:
            brand_names = json.loads(drug.brand_names)
    except:
        brand_names = []
    
    try:
        if drug.dosage_forms:
            dosage_forms = json.loads(drug.dosage_forms)
    except:
        dosage_forms = []
    
    # Get related drugs (same class)
    related_drugs = Drug.query.filter(
        Drug.drug_class_id == drug.drug_class_id,
        Drug.id != drug_id
    ).limit(6).all()
    
    return render_template('pharmacology/drug_detail.html',
                         drug=drug,
                         brand_names=brand_names,
                         dosage_forms=dosage_forms,
                         related_drugs=related_drugs)

@pharma_bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    category = request.args.get('category', 'all')
    
    results = []
    
    if query:
        # Search in drug names
        if category in ['all', 'drugs']:
            drugs = Drug.query.filter(
                db.or_(
                    Drug.name.contains(query),
                    Drug.generic_name.contains(query),
                    Drug.description.contains(query)
                )
            ).limit(20).all()
            
            for drug in drugs:
                results.append({
                    'type': 'drug',
                    'title': drug.name,
                    'subtitle': drug.generic_name or drug.drug_class.name,
                    'description': drug.description,
                    'url': url_for('pharma.drug_detail', drug_id=drug.id)
                })
        
        # Search in drug classes
        if category in ['all', 'classes']:
            drug_classes = DrugClass.query.filter(
                db.or_(
                    DrugClass.name.contains(query),
                    DrugClass.description.contains(query)
                )
            ).limit(10).all()
            
            for drug_class in drug_classes:
                results.append({
                    'type': 'class',
                    'title': drug_class.name,
                    'subtitle': f"{len(drug_class.drugs)} drugs",
                    'description': drug_class.description,
                    'url': url_for('pharma.drug_class_detail', class_id=drug_class.id)
                })
    
    return render_template('pharmacology/search.html',
                         query=query,
                         results=results,
                         category=category)

# Calculators
@pharma_bp.route('/calculators/dose', methods=['GET', 'POST'])
@login_required
def dose_calculator():
    result = None
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        try:
            weight = float(data.get('weight', 0))
            dose_per_kg = float(data.get('dose_per_kg', 0))
            frequency = int(data.get('frequency', 1))
            
            if weight <= 0 or dose_per_kg <= 0 or frequency <= 0:
                raise ValueError("All values must be positive")
            
            single_dose = weight * dose_per_kg
            daily_dose = single_dose * frequency
            
            result = {
                'single_dose': round(single_dose, 2),
                'daily_dose': round(daily_dose, 2),
                'weight': weight,
                'dose_per_kg': dose_per_kg,
                'frequency': frequency
            }
            
            if request.is_json:
                return jsonify({'success': True, 'result': result})
                
        except (ValueError, TypeError) as e:
            error = 'Please enter valid numeric values'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 400
            flash(error, 'error')
    
    return render_template('pharmacology/calculators/dose.html', result=result)

@pharma_bp.route('/calculators/drip', methods=['GET', 'POST'])
@login_required
def drip_calculator():
    result = None
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        try:
            volume = float(data.get('volume', 0))  # mL
            time_hours = float(data.get('time_hours', 0))  # hours
            drop_factor = int(data.get('drop_factor', 20))  # drops/mL
            
            if volume <= 0 or time_hours <= 0 or drop_factor <= 0:
                raise ValueError("All values must be positive")
            
            ml_per_hour = volume / time_hours
            ml_per_minute = ml_per_hour / 60
            drops_per_minute = ml_per_minute * drop_factor
            
            result = {
                'ml_per_hour': round(ml_per_hour, 1),
                'ml_per_minute': round(ml_per_minute, 2),
                'drops_per_minute': round(drops_per_minute, 0),
                'volume': volume,
                'time_hours': time_hours,
                'drop_factor': drop_factor
            }
            
            if request.is_json:
                return jsonify({'success': True, 'result': result})
                
        except (ValueError, TypeError) as e:
            error = 'Please enter valid numeric values'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 400
            flash(error, 'error')
    
    return render_template('pharmacology/calculators/drip.html', result=result)

@pharma_bp.route('/calculators/bmi', methods=['GET', 'POST'])
@login_required
def bmi_calculator():
    result = None
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        try:
            weight = float(data.get('weight', 0))  # kg
            height = float(data.get('height', 0))  # cm
            
            if weight <= 0 or height <= 0:
                raise ValueError("Weight and height must be positive")
            
            height_m = height / 100  # convert to meters
            bmi = weight / (height_m ** 2)
            
            # BMI categories
            if bmi < 18.5:
                category = 'Underweight'
                color = '#1a6ac3'
            elif bmi < 25:
                category = 'Normal weight'
                color = '#28a745'
            elif bmi < 30:
                category = 'Overweight'
                color = '#ffc107'
            else:
                category = 'Obese'
                color = '#dc3545'
            
            result = {
                'bmi': round(bmi, 1),
                'category': category,
                'color': color,
                'weight': weight,
                'height': height
            }
            
            if request.is_json:
                return jsonify({'success': True, 'result': result})
                
        except (ValueError, TypeError) as e:
            error = 'Please enter valid numeric values'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 400
            flash(error, 'error')
    
    return render_template('pharmacology/calculators/bmi.html', result=result)

@pharma_bp.route('/calculators/creatinine', methods=['GET', 'POST'])
@login_required
def creatinine_calculator():
    result = None
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        try:
            age = int(data.get('age', 0))
            weight = float(data.get('weight', 0))  # kg
            creatinine = float(data.get('creatinine', 0))  # mg/dL
            gender = data.get('gender', 'male')
            
            if age <= 0 or weight <= 0 or creatinine <= 0:
                raise ValueError("All values must be positive")
            
            # Cockcroft-Gault equation
            creatinine_clearance = ((140 - age) * weight) / (72 * creatinine)
            
            if gender == 'female':
                creatinine_clearance *= 0.85
            
            # Kidney function categories
            if creatinine_clearance >= 90:
                category = 'Normal kidney function'
                color = '#28a745'
            elif creatinine_clearance >= 60:
                category = 'Mild decrease in kidney function'
                color = '#ffc107'
            elif creatinine_clearance >= 30:
                category = 'Moderate decrease in kidney function'
                color = '#fd7e14'
            elif creatinine_clearance >= 15:
                category = 'Severe decrease in kidney function'
                color = '#dc3545'
            else:
                category = 'Kidney failure'
                color = '#6f42c1'
            
            result = {
                'creatinine_clearance': round(creatinine_clearance, 1),
                'category': category,
                'color': color,
                'age': age,
                'weight': weight,
                'creatinine': creatinine,
                'gender': gender
            }
            
            if request.is_json:
                return jsonify({'success': True, 'result': result})
                
        except (ValueError, TypeError) as e:
            error = 'Please enter valid values'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 400
            flash(error, 'error')
    
    return render_template('pharmacology/calculators/creatinine.html', result=result)

@pharma_bp.route('/calculators/pregnancy', methods=['GET', 'POST'])
@login_required
def pregnancy_calculator():
    result = None
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        try:
            lmp_date = data.get('lmp_date', '')  # Last menstrual period
            
            if not lmp_date:
                raise ValueError("Last menstrual period date is required")
            
            lmp = datetime.strptime(lmp_date, '%Y-%m-%d').date()
            
            # Calculate due date (280 days from LMP)
            from datetime import timedelta
            due_date = lmp + timedelta(days=280)
            
            # Calculate current gestational age
            today = date.today()
            days_pregnant = (today - lmp).days
            weeks = days_pregnant // 7
            days = days_pregnant % 7
            
            # Calculate trimester
            if weeks <= 12:
                trimester = 'First trimester'
                trimester_color = '#1a6ac3'
            elif weeks <= 26:
                trimester = 'Second trimester'
                trimester_color = '#28a745'
            else:
                trimester = 'Third trimester'
                trimester_color = '#ffc107'
            
            result = {
                'due_date': due_date.strftime('%B %d, %Y'),
                'weeks_pregnant': weeks,
                'days_pregnant_extra': days,
                'total_days': days_pregnant,
                'trimester': trimester,
                'trimester_color': trimester_color,
                'lmp_date': lmp_date
            }
            
            if request.is_json:
                return jsonify({'success': True, 'result': result})
                
        except (ValueError, TypeError) as e:
            error = 'Please enter a valid date'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 400
            flash(error, 'error')
    
    return render_template('pharmacology/calculators/pregnancy.html', result=result)

@pharma_bp.route('/calculators/units', methods=['GET', 'POST'])
@login_required
def unit_converter():
    result = None
    
    # Conversion factors
    conversions = {
        'weight': {
            'kg_to_lb': 2.20462,
            'lb_to_kg': 0.453592,
            'g_to_mg': 1000,
            'mg_to_g': 0.001,
            'g_to_mcg': 1000000,
            'mcg_to_g': 0.000001
        },
        'volume': {
            'l_to_ml': 1000,
            'ml_to_l': 0.001,
            'ml_to_cc': 1,
            'cc_to_ml': 1,
            'tsp_to_ml': 4.92892,
            'ml_to_tsp': 0.202884
        },
        'temperature': {
            'c_to_f': lambda c: (c * 9/5) + 32,
            'f_to_c': lambda f: (f - 32) * 5/9
        }
    }
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        try:
            value = float(data.get('value', 0))
            conversion_type = data.get('conversion_type', '')
            
            if not conversion_type:
                raise ValueError("Please select a conversion type")
            
            category, conversion = conversion_type.split('_', 1)
            
            if category == 'temperature':
                if conversion == 'to_f':
                    converted_value = conversions['temperature']['c_to_f'](value)
                    from_unit = '°C'
                    to_unit = '°F'
                else:  # to_c
                    converted_value = conversions['temperature']['f_to_c'](value)
                    from_unit = '°F'
                    to_unit = '°C'
            else:
                factor = conversions[category][conversion]
                converted_value = value * factor
                
                # Determine units based on conversion
                unit_map = {
                    'kg_to_lb': ('kg', 'lb'),
                    'lb_to_kg': ('lb', 'kg'),
                    'g_to_mg': ('g', 'mg'),
                    'mg_to_g': ('mg', 'g'),
                    'g_to_mcg': ('g', 'mcg'),
                    'mcg_to_g': ('mcg', 'g'),
                    'l_to_ml': ('L', 'mL'),
                    'ml_to_l': ('mL', 'L'),
                    'ml_to_cc': ('mL', 'cc'),
                    'cc_to_ml': ('cc', 'mL'),
                    'tsp_to_ml': ('tsp', 'mL'),
                    'ml_to_tsp': ('mL', 'tsp')
                }
                
                from_unit, to_unit = unit_map[conversion]
            
            result = {
                'original_value': value,
                'converted_value': round(converted_value, 6),
                'from_unit': from_unit,
                'to_unit': to_unit,
                'conversion_type': conversion_type
            }
            
            if request.is_json:
                return jsonify({'success': True, 'result': result})
                
        except (ValueError, TypeError) as e:
            error = 'Please enter valid values'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 400
            flash(error, 'error')
    
    return render_template('pharmacology/calculators/units.html', result=result)

@pharma_bp.route('/api/drug-suggestions')
@login_required
def api_drug_suggestions():
    """API endpoint for drug name suggestions"""
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify([])
    
    drugs = Drug.query.filter(
        db.or_(
            Drug.name.contains(query),
            Drug.generic_name.contains(query)
        )
    ).limit(10).all()
    
    suggestions = []
    for drug in drugs:
        suggestions.append({
            'id': drug.id,
            'name': drug.name,
            'generic_name': drug.generic_name,
            'class_name': drug.drug_class.name
        })
    
    return jsonify(suggestions)