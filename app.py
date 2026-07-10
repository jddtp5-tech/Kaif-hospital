from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'dev-secret-key-change-in-production'

# In-memory data structures
users = []
departments = []
appointments = []
feedbacks = []
user_id_counter = 1
department_id_counter = 1
appointment_id_counter = 1
feedback_id_counter = 1

# Initialize default departments
departments = [
    {'id': 1, 'name': 'Cardiology', 'description': 'Heart and cardiovascular care', 'location': 'Floor 2'},
    {'id': 2, 'name': 'Neurology', 'description': 'Brain and nervous system care', 'location': 'Floor 3'},
    {'id': 3, 'name': 'Orthopedics', 'description': 'Bone and joint care', 'location': 'Floor 1'},
    {'id': 4, 'name': 'Pediatrics', 'description': 'Child healthcare', 'location': 'Floor 4'},
    {'id': 5, 'name': 'General Medicine', 'description': 'General healthcare services', 'location': 'Floor 1'}
]
department_id_counter = 6

# Helper functions
def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        for user in users:
            if user['id'] == user_id:
                return user
    return None

def login_required_decorator(f):
    def wrapper(*args, **kwargs):
        if not get_current_user():
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# Make current_user available in templates
@app.context_processor
def inject_current_user():
    return dict(current_user=get_current_user())

# Routes
@app.route('/')
def index():
    current_user = get_current_user()
    if current_user:
        if current_user['role'] == 'patient':
            return redirect(url_for('patient_dashboard'))
        elif current_user['role'] == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        elif current_user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
    return render_template('index.html')

# Auth Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = None
        for u in users:
            if u['username'] == username and u['password'] == password:
                user = u
                break
        
        if user:
            session['user_id'] = user['id']
            flash('Login successful!', 'success')
            
            if user['role'] == 'patient':
                return redirect(url_for('patient_dashboard'))
            elif user['role'] == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            elif user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    global user_id_counter
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        role = request.form.get('role', 'patient')
        department_id = request.form.get('department_id')
        
        for u in users:
            if u['username'] == username:
                flash('Username already exists', 'error')
                return redirect(url_for('register'))
        
        for u in users:
            if u['email'] == email:
                flash('Email already exists', 'error')
                return redirect(url_for('register'))
        
        user = {
            'id': user_id_counter,
            'username': username,
            'email': email,
            'full_name': full_name,
            'phone': phone,
            'role': role,
            'department_id': int(department_id) if department_id else None,
            'password': password
        }
        user_id_counter += 1
        users.append(user)
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html', departments=departments)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

# Patient Routes
@app.route('/patient/dashboard')
@login_required_decorator
def patient_dashboard():
    current_user = get_current_user()
    if current_user['role'] != 'patient':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    user_appointments = [a for a in appointments if a['patient_id'] == current_user['id']]
    user_appointments.sort(key=lambda x: x['appointment_date'], reverse=True)
    
    # Enrich appointments with related data
    for apt in user_appointments:
        doctor = next((u for u in users if u['id'] == apt['doctor_id']), None)
        department = next((d for d in departments if d['id'] == apt['department_id']), None)
        apt['doctor'] = doctor
        apt['department'] = department
    
    return render_template('patient/dashboard.html', appointments=user_appointments)

@app.route('/patient/doctors')
@login_required_decorator
def patient_doctors():
    current_user = get_current_user()
    if current_user['role'] != 'patient':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    doctors = [u for u in users if u['role'] == 'doctor']
    
    # Enrich doctors with department data
    for doctor in doctors:
        if doctor['department_id']:
            department = next((d for d in departments if d['id'] == doctor['department_id']), None)
            doctor['department'] = department
        else:
            doctor['department'] = None
    
    return render_template('patient/doctors.html', departments=departments, doctors=doctors)

@app.route('/patient/book', methods=['POST'])
@login_required_decorator
def book_appointment():
    global appointment_id_counter
    current_user = get_current_user()
    if current_user['role'] != 'patient':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    doctor_id = request.form.get('doctor_id')
    department_id = request.form.get('department_id')
    appointment_date = request.form.get('appointment_date')
    reason = request.form.get('reason')
    
    if not all([doctor_id, department_id, appointment_date, reason]):
        flash('Please fill all fields', 'error')
        return redirect(url_for('patient_doctors'))
    
    try:
        appointment_date = datetime.strptime(appointment_date, '%Y-%m-%dT%H:%M')
    except ValueError:
        flash('Invalid date format', 'error')
        return redirect(url_for('patient_doctors'))
    
    appointment = {
        'id': appointment_id_counter,
        'patient_id': current_user['id'],
        'doctor_id': int(doctor_id),
        'department_id': int(department_id),
        'appointment_date': appointment_date,
        'reason': reason,
        'status': 'pending',
        'created_at': datetime.now()
    }
    appointment_id_counter += 1
    appointments.append(appointment)
    
    flash('Appointment booked successfully!', 'success')
    return redirect(url_for('patient_dashboard'))

@app.route('/patient/cancel/<int:appointment_id>')
@login_required_decorator
def cancel_appointment(appointment_id):
    current_user = get_current_user()
    if current_user['role'] != 'patient':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    appointment = None
    for a in appointments:
        if a['id'] == appointment_id:
            appointment = a
            break
    
    if not appointment:
        flash('Appointment not found', 'error')
        return redirect(url_for('patient_dashboard'))
    
    if appointment['patient_id'] != current_user['id']:
        flash('Access denied', 'error')
        return redirect(url_for('patient_dashboard'))
    
    appointment['status'] = 'cancelled'
    
    flash('Appointment cancelled', 'info')
    return redirect(url_for('patient_dashboard'))

@app.route('/patient/feedback/<int:appointment_id>', methods=['GET', 'POST'])
@login_required_decorator
def submit_feedback(appointment_id):
    global feedback_id_counter
    current_user = get_current_user()
    if current_user['role'] != 'patient':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    appointment = None
    for a in appointments:
        if a['id'] == appointment_id:
            appointment = a
            break
    
    if not appointment:
        flash('Appointment not found', 'error')
        return redirect(url_for('patient_dashboard'))
    
    if appointment['patient_id'] != current_user['id']:
        flash('Access denied', 'error')
        return redirect(url_for('patient_dashboard'))
    
    if request.method == 'POST':
        rating = request.form.get('rating')
        comment = request.form.get('comment')
        
        feedback = {
            'id': feedback_id_counter,
            'user_id': current_user['id'],
            'appointment_id': appointment_id,
            'rating': int(rating),
            'comment': comment,
            'created_at': datetime.now()
        }
        feedback_id_counter += 1
        feedbacks.append(feedback)
        
        flash('Feedback submitted successfully!', 'success')
        return redirect(url_for('patient_dashboard'))
    
    return render_template('patient/feedback.html', appointment=appointment)

# Doctor Routes
@app.route('/doctor/dashboard')
@login_required_decorator
def doctor_dashboard():
    current_user = get_current_user()
    if current_user['role'] != 'doctor':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    doctor_appointments = [a for a in appointments if a['doctor_id'] == current_user['id']]
    doctor_appointments.sort(key=lambda x: x['appointment_date'], reverse=True)
    
    # Enrich appointments with related data
    for apt in doctor_appointments:
        patient = next((u for u in users if u['id'] == apt['patient_id']), None)
        department = next((d for d in departments if d['id'] == apt['department_id']), None)
        apt['patient'] = patient
        apt['department'] = department
    
    return render_template('doctor/dashboard.html', appointments=doctor_appointments)

@app.route('/doctor/update/<int:appointment_id>', methods=['POST'])
@login_required_decorator
def update_appointment(appointment_id):
    current_user = get_current_user()
    if current_user['role'] != 'doctor':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    appointment = None
    for a in appointments:
        if a['id'] == appointment_id:
            appointment = a
            break
    
    if not appointment:
        flash('Appointment not found', 'error')
        return redirect(url_for('doctor_dashboard'))
    
    if appointment['doctor_id'] != current_user['id']:
        flash('Access denied', 'error')
        return redirect(url_for('doctor_dashboard'))
    
    status = request.form.get('status')
    
    if status in ['pending', 'confirmed', 'completed', 'cancelled']:
        appointment['status'] = status
        flash('Appointment status updated', 'success')
    else:
        flash('Invalid status', 'error')
    
    return redirect(url_for('doctor_dashboard'))

# Admin Routes
@app.route('/admin/dashboard')
@login_required_decorator
def admin_dashboard():
    current_user = get_current_user()
    if current_user['role'] != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    sorted_appointments = sorted(appointments, key=lambda x: x['created_at'], reverse=True)
    sorted_feedbacks = sorted(feedbacks, key=lambda x: x['created_at'], reverse=True)
    
    # Enrich appointments with related data
    for apt in sorted_appointments:
        patient = next((u for u in users if u['id'] == apt['patient_id']), None)
        doctor = next((u for u in users if u['id'] == apt['doctor_id']), None)
        department = next((d for d in departments if d['id'] == apt['department_id']), None)
        apt['patient'] = patient
        apt['doctor'] = doctor
        apt['department'] = department
    
    # Enrich feedbacks with related data
    for fb in sorted_feedbacks:
        user = next((u for u in users if u['id'] == fb['user_id']), None)
        fb['user'] = user
    
    return render_template('admin/dashboard.html', 
                         appointments=sorted_appointments, 
                         users=users, 
                         departments=departments,
                         feedbacks=sorted_feedbacks)

@app.route('/admin/department/add', methods=['POST'])
@login_required_decorator
def add_department():
    global department_id_counter
    current_user = get_current_user()
    if current_user['role'] != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    name = request.form.get('name')
    description = request.form.get('description')
    location = request.form.get('location')
    
    for dept in departments:
        if dept['name'] == name:
            flash('Department already exists', 'error')
            return redirect(url_for('admin_dashboard'))
    
    department = {
        'id': department_id_counter,
        'name': name,
        'description': description,
        'location': location
    }
    department_id_counter += 1
    departments.append(department)
    
    flash('Department added successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/department/delete/<int:department_id>')
@login_required_decorator
def delete_department(department_id):
    current_user = get_current_user()
    if current_user['role'] != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    for i, dept in enumerate(departments):
        if dept['id'] == department_id:
            departments.pop(i)
            break
    
    flash('Department deleted', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/department/edit/<int:department_id>', methods=['GET', 'POST'])
@login_required_decorator
def edit_department(department_id):
    current_user = get_current_user()
    if current_user['role'] != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    department = None
    for d in departments:
        if d['id'] == department_id:
            department = d
            break
    
    if not department:
        flash('Department not found', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        department['name'] = request.form.get('name')
        department['description'] = request.form.get('description')
        department['location'] = request.form.get('location')
        
        flash('Department updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/edit_department.html', department=department)

@app.route('/admin/user/delete/<int:user_id>')
@login_required_decorator
def delete_user(user_id):
    current_user = get_current_user()
    if current_user['role'] != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    if user_id == current_user['id']:
        flash('Cannot delete yourself', 'error')
        return redirect(url_for('admin_dashboard'))
    
    for i, user in enumerate(users):
        if user['id'] == user_id:
            users.pop(i)
            break
    
    flash('User deleted', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required_decorator
def edit_user(user_id):
    current_user = get_current_user()
    if current_user['role'] != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    user = None
    for u in users:
        if u['id'] == user_id:
            user = u
            break
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        user['full_name'] = request.form.get('full_name')
        user['email'] = request.form.get('email')
        user['phone'] = request.form.get('phone')
        user['role'] = request.form.get('role')
        dept_id = request.form.get('department_id')
        user['department_id'] = int(dept_id) if dept_id else None
        
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/edit_user.html', user=user, departments=departments)

@app.route('/admin/appointment/update/<int:appointment_id>', methods=['POST'])
@login_required_decorator
def admin_update_appointment(appointment_id):
    current_user = get_current_user()
    if current_user['role'] != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    appointment = None
    for a in appointments:
        if a['id'] == appointment_id:
            appointment = a
            break
    
    if not appointment:
        flash('Appointment not found', 'error')
        return redirect(url_for('admin_dashboard'))
    
    status = request.form.get('status')
    
    if status in ['pending', 'confirmed', 'completed', 'cancelled']:
        appointment['status'] = status
        flash('Appointment status updated', 'success')
    else:
        flash('Invalid status', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/appointment/delete/<int:appointment_id>')
@login_required_decorator
def admin_delete_appointment(appointment_id):
    current_user = get_current_user()
    if current_user['role'] != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    for i, apt in enumerate(appointments):
        if apt['id'] == appointment_id:
            appointments.pop(i)
            break
    
    flash('Appointment deleted', 'info')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
