-- city_hospital: 50-table demo database (generated rows). Run once in MySQL Workbench (⚡).
-- Creates ONLY the new database `city_hospital`; nothing else is touched.
DROP DATABASE IF EXISTS city_hospital;
CREATE DATABASE city_hospital;
USE city_hospital;

-- helper numbers 1..10000 (dropped at the end)
CREATE TABLE _digits (d INT);
INSERT INTO _digits VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9);
CREATE TABLE _numbers (n INT PRIMARY KEY);
INSERT INTO _numbers SELECT a.d*1000 + b.d*100 + c.d*10 + e.d + 1 FROM _digits a, _digits b, _digits c, _digits e;

CREATE TABLE departments (
  id INT PRIMARY KEY,
  dept_name VARCHAR(50),
  floor_no INT,
  phone_ext VARCHAR(10)
);
INSERT INTO departments (id, dept_name, floor_no, phone_ext)
SELECT n, ELT(1 + MOD(n-1, 20), 'Cardiology', 'Neurology', 'Orthopedics', 'Pediatrics', 'Oncology', 'Dermatology', 'Radiology', 'Emergency', 'General Medicine', 'General Surgery', 'Gynecology', 'Psychiatry', 'Ophthalmology', 'ENT', 'Urology', 'Nephrology', 'Gastroenterology', 'Pulmonology', 'Endocrinology', 'Anesthesiology'), 1 + MOD(n, 6), CONCAT('x', 200 + n)
FROM _numbers WHERE n <= 20;

CREATE TABLE staff_roles (
  id INT PRIMARY KEY,
  role_name VARCHAR(50)
);
INSERT INTO staff_roles (id, role_name)
SELECT n, ELT(1 + MOD(n-1, 10), 'Receptionist', 'Pharmacist', 'Lab Technician', 'Radiographer', 'Cleaner', 'Security', 'Accountant', 'IT Support', 'Dietician', 'Porter')
FROM _numbers WHERE n <= 10;

CREATE TABLE doctors (
  id INT PRIMARY KEY,
  full_name VARCHAR(80),
  specialty VARCHAR(50),
  dept_id INT,
  hire_date DATE,
  consultation_fee DECIMAL(10,2),
  FOREIGN KEY (dept_id) REFERENCES departments(id)
);
INSERT INTO doctors (id, full_name, specialty, dept_id, hire_date, consultation_fee)
SELECT n, CONCAT('Dr. ', CONCAT(ELT(1 + MOD(n*1, 20), 'Aarav', 'Priya', 'Rohan', 'Ananya', 'Vikram', 'Sneha', 'Arjun', 'Kavya', 'Rahul', 'Isha', 'Karan', 'Meera', 'Aditya', 'Pooja', 'Nikhil', 'Riya', 'Siddharth', 'Neha', 'Varun', 'Diya'), ' ', ELT(1 + MOD(n*1*7+3, 20), 'Sharma', 'Verma', 'Patel', 'Iyer', 'Reddy', 'Nair', 'Gupta', 'Mehta', 'Joshi', 'Rao', 'Singh', 'Das', 'Kapoor', 'Malhotra', 'Bose', 'Pillai', 'Chopra', 'Kulkarni', 'Menon', 'Saxena'))), ELT(1 + MOD(n, 10), 'Cardiology', 'Neurology', 'Orthopedics', 'Pediatrics', 'Oncology', 'Dermatology', 'Radiology', 'Emergency', 'General Medicine', 'General Surgery'), 1 + MOD(n*7, 20), DATE_ADD('2010-01-01', INTERVAL MOD(n*13, 4000) DAY), ROUND(300 + MOD(n*37, 1200) + MOD(n, 100) / 100, 2)
FROM _numbers WHERE n <= 60;

CREATE TABLE nurses (
  id INT PRIMARY KEY,
  full_name VARCHAR(80),
  dept_id INT,
  shift_preference VARCHAR(20),
  hire_date DATE,
  FOREIGN KEY (dept_id) REFERENCES departments(id)
);
INSERT INTO nurses (id, full_name, dept_id, shift_preference, hire_date)
SELECT n, CONCAT(ELT(1 + MOD(n*3, 20), 'Aarav', 'Priya', 'Rohan', 'Ananya', 'Vikram', 'Sneha', 'Arjun', 'Kavya', 'Rahul', 'Isha', 'Karan', 'Meera', 'Aditya', 'Pooja', 'Nikhil', 'Riya', 'Siddharth', 'Neha', 'Varun', 'Diya'), ' ', ELT(1 + MOD(n*3*7+3, 20), 'Sharma', 'Verma', 'Patel', 'Iyer', 'Reddy', 'Nair', 'Gupta', 'Mehta', 'Joshi', 'Rao', 'Singh', 'Das', 'Kapoor', 'Malhotra', 'Bose', 'Pillai', 'Chopra', 'Kulkarni', 'Menon', 'Saxena')), 1 + MOD(n*3, 20), ELT(1 + MOD(n, 3), 'Day', 'Night', 'Rotating'), DATE_ADD('2012-01-01', INTERVAL MOD(n*13, 4000) DAY)
FROM _numbers WHERE n <= 80;

CREATE TABLE support_staff (
  id INT PRIMARY KEY,
  full_name VARCHAR(80),
  role_id INT,
  dept_id INT,
  monthly_salary DECIMAL(10,2),
  FOREIGN KEY (role_id) REFERENCES staff_roles(id),
  FOREIGN KEY (dept_id) REFERENCES departments(id)
);
INSERT INTO support_staff (id, full_name, role_id, dept_id, monthly_salary)
SELECT n, CONCAT(ELT(1 + MOD(n*5, 20), 'Aarav', 'Priya', 'Rohan', 'Ananya', 'Vikram', 'Sneha', 'Arjun', 'Kavya', 'Rahul', 'Isha', 'Karan', 'Meera', 'Aditya', 'Pooja', 'Nikhil', 'Riya', 'Siddharth', 'Neha', 'Varun', 'Diya'), ' ', ELT(1 + MOD(n*5*7+3, 20), 'Sharma', 'Verma', 'Patel', 'Iyer', 'Reddy', 'Nair', 'Gupta', 'Mehta', 'Joshi', 'Rao', 'Singh', 'Das', 'Kapoor', 'Malhotra', 'Bose', 'Pillai', 'Chopra', 'Kulkarni', 'Menon', 'Saxena')), 1 + MOD(n*7, 10), 1 + MOD(n*11, 20), ROUND(15000 + MOD(n*37, 30000) + MOD(n, 100) / 100, 2)
FROM _numbers WHERE n <= 50;

CREATE TABLE wards (
  id INT PRIMARY KEY,
  ward_name VARCHAR(30),
  dept_id INT,
  capacity INT,
  FOREIGN KEY (dept_id) REFERENCES departments(id)
);
INSERT INTO wards (id, ward_name, dept_id, capacity)
SELECT n, CONCAT('Ward ', n), 1 + MOD(n*7, 20), 10 + MOD(n*3, 30)
FROM _numbers WHERE n <= 25;

CREATE TABLE rooms (
  id INT PRIMARY KEY,
  ward_id INT,
  room_number VARCHAR(10),
  room_type VARCHAR(20),
  FOREIGN KEY (ward_id) REFERENCES wards(id)
);
INSERT INTO rooms (id, ward_id, room_number, room_type)
SELECT n, 1 + MOD(n*7, 25), CONCAT('R', 100 + n), ELT(1 + MOD(n, 4), 'General', 'Semi-private', 'Private', 'ICU')
FROM _numbers WHERE n <= 120;

CREATE TABLE beds (
  id INT PRIMARY KEY,
  room_id INT,
  bed_label VARCHAR(10),
  is_occupied BOOLEAN,
  FOREIGN KEY (room_id) REFERENCES rooms(id)
);
INSERT INTO beds (id, room_id, bed_label, is_occupied)
SELECT n, 1 + MOD(n*7, 120), CONCAT('B', n), MOD(n, 3) = 0
FROM _numbers WHERE n <= 300;

CREATE TABLE patients (
  id INT PRIMARY KEY,
  full_name VARCHAR(80),
  gender VARCHAR(10),
  birth_date DATE,
  blood_group VARCHAR(5),
  city VARCHAR(30),
  registered_on DATE
);
INSERT INTO patients (id, full_name, gender, birth_date, blood_group, city, registered_on)
SELECT n, CONCAT(ELT(1 + MOD(n*11, 20), 'Aarav', 'Priya', 'Rohan', 'Ananya', 'Vikram', 'Sneha', 'Arjun', 'Kavya', 'Rahul', 'Isha', 'Karan', 'Meera', 'Aditya', 'Pooja', 'Nikhil', 'Riya', 'Siddharth', 'Neha', 'Varun', 'Diya'), ' ', ELT(1 + MOD(n*11*7+3, 20), 'Sharma', 'Verma', 'Patel', 'Iyer', 'Reddy', 'Nair', 'Gupta', 'Mehta', 'Joshi', 'Rao', 'Singh', 'Das', 'Kapoor', 'Malhotra', 'Bose', 'Pillai', 'Chopra', 'Kulkarni', 'Menon', 'Saxena')), ELT(1 + MOD(n, 3), 'Male', 'Female', 'Other'), DATE_SUB('2015-01-01', INTERVAL MOD(n*97, 25000) DAY), ELT(1 + MOD(n, 8), 'A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'), ELT(1 + MOD(n*3, 10), 'Mumbai', 'Pune', 'Delhi', 'Bengaluru', 'Chennai', 'Hyderabad', 'Kolkata', 'Ahmedabad', 'Jaipur', 'Lucknow'), DATE_ADD('2022-01-01', INTERVAL MOD(n*13, 1000) DAY)
FROM _numbers WHERE n <= 500;

CREATE TABLE insurance_providers (
  id INT PRIMARY KEY,
  provider_name VARCHAR(60),
  coverage_percent INT
);
INSERT INTO insurance_providers (id, provider_name, coverage_percent)
SELECT n, ELT(1 + MOD(n-1, 12), 'Star Health', 'HDFC Ergo', 'ICICI Lombard', 'Niva Bupa', 'Care Health', 'Bajaj Allianz', 'Tata AIG', 'New India Assurance', 'United India', 'Oriental Insurance', 'Aditya Birla Health', 'ManipalCigna'), 50 + MOD(n*7, 45)
FROM _numbers WHERE n <= 12;

CREATE TABLE patient_insurance (
  id INT PRIMARY KEY,
  patient_id INT,
  provider_id INT,
  policy_number VARCHAR(20),
  valid_until DATE,
  FOREIGN KEY (patient_id) REFERENCES patients(id),
  FOREIGN KEY (provider_id) REFERENCES insurance_providers(id)
);
INSERT INTO patient_insurance (id, patient_id, provider_id, policy_number, valid_until)
SELECT n, 1 + MOD(n*7, 500), 1 + MOD(n*7, 12), CONCAT('POL', 10000 + n), DATE_ADD('2025-01-01', INTERVAL MOD(n*13, 900) DAY)
FROM _numbers WHERE n <= 400;

CREATE TABLE appointments (
  id INT PRIMARY KEY,
  patient_id INT,
  doctor_id INT,
  appointment_date DATE,
  status VARCHAR(20),
  reason VARCHAR(50),
  FOREIGN KEY (patient_id) REFERENCES patients(id),
  FOREIGN KEY (doctor_id) REFERENCES doctors(id)
);
INSERT INTO appointments (id, patient_id, doctor_id, appointment_date, status, reason)
SELECT n, 1 + MOD(n*13, 500), 1 + MOD(n*7, 60), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY), ELT(1 + MOD(n, 5), 'Completed', 'Completed', 'Scheduled', 'Cancelled', 'No-show'), ELT(1 + MOD(n*3, 8), 'Fever', 'Follow-up', 'Chest pain', 'Back pain', 'Headache', 'Routine checkup', 'Cough', 'Injury')
FROM _numbers WHERE n <= 1500;

CREATE TABLE admissions (
  id INT PRIMARY KEY,
  patient_id INT,
  bed_id INT,
  admitted_on DATE,
  discharged_on DATE,
  admission_type VARCHAR(20),
  FOREIGN KEY (patient_id) REFERENCES patients(id),
  FOREIGN KEY (bed_id) REFERENCES beds(id)
);
INSERT INTO admissions (id, patient_id, bed_id, admitted_on, discharged_on, admission_type)
SELECT n, 1 + MOD(n*17, 500), 1 + MOD(n*7, 300), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY), DATE_ADD(DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY), INTERVAL 1 + MOD(n, 14) DAY), ELT(1 + MOD(n, 3), 'Emergency', 'Planned', 'Transfer')
FROM _numbers WHERE n <= 600;

CREATE TABLE diagnosis_catalog (
  id INT PRIMARY KEY,
  icd_code VARCHAR(10),
  diagnosis_name VARCHAR(60)
);
INSERT INTO diagnosis_catalog (id, icd_code, diagnosis_name)
SELECT n, CONCAT('D', LPAD(n, 3, '0')), CONCAT(ELT(1 + MOD(n-1, 12), 'Hypertension', 'Diabetes', 'Asthma', 'Migraine', 'Pneumonia', 'Fracture', 'Anemia', 'Arthritis', 'Bronchitis', 'Gastritis', 'Dengue', 'Typhoid'), ' stage ', 1 + FLOOR((n-1) / 12))
FROM _numbers WHERE n <= 60;

CREATE TABLE patient_diagnoses (
  id INT PRIMARY KEY,
  appointment_id INT,
  diagnosis_id INT,
  diagnosed_on DATE,
  FOREIGN KEY (appointment_id) REFERENCES appointments(id),
  FOREIGN KEY (diagnosis_id) REFERENCES diagnosis_catalog(id)
);
INSERT INTO patient_diagnoses (id, appointment_id, diagnosis_id, diagnosed_on)
SELECT n, 1 + MOD(n*7, 1500), 1 + MOD(n*7, 60), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY)
FROM _numbers WHERE n <= 1200;

CREATE TABLE medicines (
  id INT PRIMARY KEY,
  medicine_name VARCHAR(60),
  category VARCHAR(30),
  unit_price DECIMAL(10,2)
);
INSERT INTO medicines (id, medicine_name, category, unit_price)
SELECT n, CONCAT(ELT(1 + MOD(n-1, 20), 'Paracetamol', 'Amoxicillin', 'Metformin', 'Atorvastatin', 'Amlodipine', 'Omeprazole', 'Cetirizine', 'Ibuprofen', 'Azithromycin', 'Losartan', 'Pantoprazole', 'Insulin', 'Salbutamol', 'Prednisolone', 'Clopidogrel', 'Levothyroxine', 'Vitamin D3', 'Ondansetron', 'Diclofenac', 'Ranitidine'), ' ', 5 * (1 + FLOOR((n-1) / 20)), 'mg'), ELT(1 + MOD(n, 6), 'Antibiotic', 'Painkiller', 'Antidiabetic', 'Cardiac', 'Antacid', 'Antihistamine'), ROUND(2 + MOD(n*37, 300) + MOD(n, 100) / 100, 2)
FROM _numbers WHERE n <= 200;

CREATE TABLE medicine_suppliers (
  id INT PRIMARY KEY,
  supplier_name VARCHAR(60),
  city VARCHAR(30),
  contact_person VARCHAR(80)
);
INSERT INTO medicine_suppliers (id, supplier_name, city, contact_person)
SELECT n, CONCAT('MedSupply ', n), ELT(1 + MOD(n, 10), 'Mumbai', 'Pune', 'Delhi', 'Bengaluru', 'Chennai', 'Hyderabad', 'Kolkata', 'Ahmedabad', 'Jaipur', 'Lucknow'), CONCAT(ELT(1 + MOD(n*19, 20), 'Aarav', 'Priya', 'Rohan', 'Ananya', 'Vikram', 'Sneha', 'Arjun', 'Kavya', 'Rahul', 'Isha', 'Karan', 'Meera', 'Aditya', 'Pooja', 'Nikhil', 'Riya', 'Siddharth', 'Neha', 'Varun', 'Diya'), ' ', ELT(1 + MOD(n*19*7+3, 20), 'Sharma', 'Verma', 'Patel', 'Iyer', 'Reddy', 'Nair', 'Gupta', 'Mehta', 'Joshi', 'Rao', 'Singh', 'Das', 'Kapoor', 'Malhotra', 'Bose', 'Pillai', 'Chopra', 'Kulkarni', 'Menon', 'Saxena'))
FROM _numbers WHERE n <= 15;

CREATE TABLE medicine_batches (
  id INT PRIMARY KEY,
  medicine_id INT,
  supplier_id INT,
  batch_code VARCHAR(20),
  expiry_date DATE,
  quantity INT,
  FOREIGN KEY (medicine_id) REFERENCES medicines(id),
  FOREIGN KEY (supplier_id) REFERENCES medicine_suppliers(id)
);
INSERT INTO medicine_batches (id, medicine_id, supplier_id, batch_code, expiry_date, quantity)
SELECT n, 1 + MOD(n*7, 200), 1 + MOD(n*7, 15), CONCAT('BT', 50000 + n), DATE_ADD('2025-06-01', INTERVAL MOD(n*13, 900) DAY), 50 + MOD(n*17, 950)
FROM _numbers WHERE n <= 500;

CREATE TABLE prescriptions (
  id INT PRIMARY KEY,
  appointment_id INT,
  doctor_id INT,
  issued_on DATE,
  FOREIGN KEY (appointment_id) REFERENCES appointments(id),
  FOREIGN KEY (doctor_id) REFERENCES doctors(id)
);
INSERT INTO prescriptions (id, appointment_id, doctor_id, issued_on)
SELECT n, n, 1 + MOD(n*7, 60), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY)
FROM _numbers WHERE n <= 1500;

CREATE TABLE prescription_items (
  id INT PRIMARY KEY,
  prescription_id INT,
  medicine_id INT,
  dosage VARCHAR(20),
  days INT,
  FOREIGN KEY (prescription_id) REFERENCES prescriptions(id),
  FOREIGN KEY (medicine_id) REFERENCES medicines(id)
);
INSERT INTO prescription_items (id, prescription_id, medicine_id, dosage, days)
SELECT n, 1 + MOD(n*7, 1500), 1 + MOD(n*11, 200), ELT(1 + MOD(n, 5), '1-0-1', '1-1-1', '0-0-1', '1-0-0', 'SOS'), 1 + MOD(n, 14)
FROM _numbers WHERE n <= 3500;

CREATE TABLE pharmacy_dispenses (
  id INT PRIMARY KEY,
  prescription_item_id INT,
  dispensed_on DATE,
  quantity INT,
  FOREIGN KEY (prescription_item_id) REFERENCES prescription_items(id)
);
INSERT INTO pharmacy_dispenses (id, prescription_item_id, dispensed_on, quantity)
SELECT n, 1 + MOD(n*7, 3500), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY), 1 + MOD(n*3, 30)
FROM _numbers WHERE n <= 3000;

CREATE TABLE lab_test_catalog (
  id INT PRIMARY KEY,
  test_name VARCHAR(60),
  sample_type VARCHAR(20),
  price DECIMAL(10,2)
);
INSERT INTO lab_test_catalog (id, test_name, sample_type, price)
SELECT n, CONCAT(ELT(1 + MOD(n-1, 10), 'Complete Blood Count', 'Lipid Profile', 'Blood Sugar', 'Thyroid Panel', 'Liver Function', 'Kidney Function', 'Urine Routine', 'Vitamin B12', 'HbA1c', 'Dengue NS1'), ' ', ELT(1 + FLOOR((n-1) / 10), 'A', 'B', 'C', 'D')), ELT(1 + MOD(n, 4), 'Blood', 'Urine', 'Saliva', 'Tissue'), ROUND(150 + MOD(n*37, 2500) + MOD(n, 100) / 100, 2)
FROM _numbers WHERE n <= 40;

CREATE TABLE lab_orders (
  id INT PRIMARY KEY,
  patient_id INT,
  doctor_id INT,
  test_id INT,
  ordered_on DATE,
  priority VARCHAR(10),
  FOREIGN KEY (patient_id) REFERENCES patients(id),
  FOREIGN KEY (doctor_id) REFERENCES doctors(id),
  FOREIGN KEY (test_id) REFERENCES lab_test_catalog(id)
);
INSERT INTO lab_orders (id, patient_id, doctor_id, test_id, ordered_on, priority)
SELECT n, 1 + MOD(n*19, 500), 1 + MOD(n*11, 60), 1 + MOD(n*7, 40), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY), ELT(1 + MOD(n, 4), 'Routine', 'Routine', 'Urgent', 'STAT')
FROM _numbers WHERE n <= 1800;

CREATE TABLE lab_results (
  id INT PRIMARY KEY,
  lab_order_id INT,
  result_value DECIMAL(10,2),
  result_flag VARCHAR(10),
  reported_on DATE,
  FOREIGN KEY (lab_order_id) REFERENCES lab_orders(id)
);
INSERT INTO lab_results (id, lab_order_id, result_value, result_flag, reported_on)
SELECT n, n, ROUND(1 + MOD(n*37, 400) + MOD(n, 100) / 100, 2), ELT(1 + MOD(n, 5), 'Normal', 'Normal', 'High', 'Low', 'Critical'), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY)
FROM _numbers WHERE n <= 1700;

CREATE TABLE procedure_catalog (
  id INT PRIMARY KEY,
  procedure_name VARCHAR(60),
  base_cost DECIMAL(10,2)
);
INSERT INTO procedure_catalog (id, procedure_name, base_cost)
SELECT n, CONCAT(ELT(1 + MOD(n-1, 10), 'Appendectomy', 'Angioplasty', 'Knee Replacement', 'Cataract Surgery', 'C-Section', 'Hernia Repair', 'Bypass Surgery', 'Gallbladder Removal', 'Tonsillectomy', 'Spinal Fusion'), ' type ', 1 + FLOOR((n-1) / 10)), ROUND(20000 + MOD(n*37, 300000) + MOD(n, 100) / 100, 2)
FROM _numbers WHERE n <= 50;

CREATE TABLE operating_theatres (
  id INT PRIMARY KEY,
  theatre_name VARCHAR(30),
  floor_no INT
);
INSERT INTO operating_theatres (id, theatre_name, floor_no)
SELECT n, CONCAT('OT-', n), 1 + MOD(n, 3)
FROM _numbers WHERE n <= 8;

CREATE TABLE surgeries (
  id INT PRIMARY KEY,
  admission_id INT,
  procedure_id INT,
  surgeon_id INT,
  theatre_id INT,
  surgery_date DATE,
  duration_minutes INT,
  FOREIGN KEY (admission_id) REFERENCES admissions(id),
  FOREIGN KEY (procedure_id) REFERENCES procedure_catalog(id),
  FOREIGN KEY (surgeon_id) REFERENCES doctors(id),
  FOREIGN KEY (theatre_id) REFERENCES operating_theatres(id)
);
INSERT INTO surgeries (id, admission_id, procedure_id, surgeon_id, theatre_id, surgery_date, duration_minutes)
SELECT n, 1 + MOD(n*7, 600), 1 + MOD(n*7, 50), 1 + MOD(n*13, 60), 1 + MOD(n*7, 8), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY), 30 + MOD(n*11, 300)
FROM _numbers WHERE n <= 300;

CREATE TABLE invoices (
  id INT PRIMARY KEY,
  patient_id INT,
  invoice_date DATE,
  total_amount DECIMAL(12,2),
  status VARCHAR(10),
  FOREIGN KEY (patient_id) REFERENCES patients(id)
);
INSERT INTO invoices (id, patient_id, invoice_date, total_amount, status)
SELECT n, 1 + MOD(n*23, 500), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY), ROUND(500 + MOD(n*37, 80000) + MOD(n, 100) / 100, 2), ELT(1 + MOD(n, 4), 'Paid', 'Paid', 'Pending', 'Overdue')
FROM _numbers WHERE n <= 1500;

CREATE TABLE invoice_items (
  id INT PRIMARY KEY,
  invoice_id INT,
  description VARCHAR(40),
  amount DECIMAL(12,2),
  FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);
INSERT INTO invoice_items (id, invoice_id, description, amount)
SELECT n, 1 + MOD(n*7, 1500), ELT(1 + MOD(n, 6), 'Consultation', 'Room charges', 'Medicines', 'Lab tests', 'Surgery', 'Nursing'), ROUND(100 + MOD(n*37, 20000) + MOD(n, 100) / 100, 2)
FROM _numbers WHERE n <= 4000;

CREATE TABLE invoice_settlements (
  id INT PRIMARY KEY,
  invoice_id INT,
  settled_on DATE,
  amount DECIMAL(12,2),
  method VARCHAR(15),
  FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);
INSERT INTO invoice_settlements (id, invoice_id, settled_on, amount, method)
SELECT n, n, DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY), ROUND(500 + MOD(n*37, 80000) + MOD(n, 100) / 100, 2), ELT(1 + MOD(n, 4), 'Cash', 'Card', 'UPI', 'Insurance')
FROM _numbers WHERE n <= 1300;

CREATE TABLE insurance_claims (
  id INT PRIMARY KEY,
  policy_id INT,
  invoice_id INT,
  claim_amount DECIMAL(12,2),
  claim_status VARCHAR(25),
  FOREIGN KEY (policy_id) REFERENCES patient_insurance(id),
  FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);
INSERT INTO insurance_claims (id, policy_id, invoice_id, claim_amount, claim_status)
SELECT n, 1 + MOD(n*7, 400), 1 + MOD(n*3, 1500), ROUND(1000 + MOD(n*37, 60000) + MOD(n, 100) / 100, 2), ELT(1 + MOD(n, 4), 'Approved', 'Rejected', 'Pending', 'Partially approved')
FROM _numbers WHERE n <= 700;

CREATE TABLE ambulances (
  id INT PRIMARY KEY,
  vehicle_number VARCHAR(20),
  vehicle_type VARCHAR(20)
);
INSERT INTO ambulances (id, vehicle_number, vehicle_type)
SELECT n, CONCAT('MH12-AB-', 1000 + n), ELT(1 + MOD(n, 3), 'Basic', 'Advanced', 'Neonatal')
FROM _numbers WHERE n <= 15;

CREATE TABLE ambulance_drivers (
  id INT PRIMARY KEY,
  full_name VARCHAR(80),
  license_number VARCHAR(20)
);
INSERT INTO ambulance_drivers (id, full_name, license_number)
SELECT n, CONCAT(ELT(1 + MOD(n*29, 20), 'Aarav', 'Priya', 'Rohan', 'Ananya', 'Vikram', 'Sneha', 'Arjun', 'Kavya', 'Rahul', 'Isha', 'Karan', 'Meera', 'Aditya', 'Pooja', 'Nikhil', 'Riya', 'Siddharth', 'Neha', 'Varun', 'Diya'), ' ', ELT(1 + MOD(n*29*7+3, 20), 'Sharma', 'Verma', 'Patel', 'Iyer', 'Reddy', 'Nair', 'Gupta', 'Mehta', 'Joshi', 'Rao', 'Singh', 'Das', 'Kapoor', 'Malhotra', 'Bose', 'Pillai', 'Chopra', 'Kulkarni', 'Menon', 'Saxena')), CONCAT('DL', 700000 + n)
FROM _numbers WHERE n <= 25;

CREATE TABLE ambulance_trips (
  id INT PRIMARY KEY,
  ambulance_id INT,
  driver_id INT,
  patient_id INT,
  trip_date DATE,
  distance_km DECIMAL(6,1),
  FOREIGN KEY (ambulance_id) REFERENCES ambulances(id),
  FOREIGN KEY (driver_id) REFERENCES ambulance_drivers(id),
  FOREIGN KEY (patient_id) REFERENCES patients(id)
);
INSERT INTO ambulance_trips (id, ambulance_id, driver_id, patient_id, trip_date, distance_km)
SELECT n, 1 + MOD(n*7, 15), 1 + MOD(n*7, 25), 1 + MOD(n*29, 500), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY), ROUND(1 + MOD(n*7, 60) + MOD(n, 10) / 10, 1)
FROM _numbers WHERE n <= 800;

CREATE TABLE blood_donors (
  id INT PRIMARY KEY,
  full_name VARCHAR(80),
  blood_group VARCHAR(5),
  last_donation DATE
);
INSERT INTO blood_donors (id, full_name, blood_group, last_donation)
SELECT n, CONCAT(ELT(1 + MOD(n*31, 20), 'Aarav', 'Priya', 'Rohan', 'Ananya', 'Vikram', 'Sneha', 'Arjun', 'Kavya', 'Rahul', 'Isha', 'Karan', 'Meera', 'Aditya', 'Pooja', 'Nikhil', 'Riya', 'Siddharth', 'Neha', 'Varun', 'Diya'), ' ', ELT(1 + MOD(n*31*7+3, 20), 'Sharma', 'Verma', 'Patel', 'Iyer', 'Reddy', 'Nair', 'Gupta', 'Mehta', 'Joshi', 'Rao', 'Singh', 'Das', 'Kapoor', 'Malhotra', 'Bose', 'Pillai', 'Chopra', 'Kulkarni', 'Menon', 'Saxena')), ELT(1 + MOD(n*3, 8), 'A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY)
FROM _numbers WHERE n <= 300;

CREATE TABLE blood_donations (
  id INT PRIMARY KEY,
  donor_id INT,
  donated_on DATE,
  units INT,
  FOREIGN KEY (donor_id) REFERENCES blood_donors(id)
);
INSERT INTO blood_donations (id, donor_id, donated_on, units)
SELECT n, 1 + MOD(n*7, 300), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY), 1 + MOD(n, 2)
FROM _numbers WHERE n <= 600;

CREATE TABLE blood_inventory (
  id INT PRIMARY KEY,
  blood_group VARCHAR(5),
  units_available INT
);
INSERT INTO blood_inventory (id, blood_group, units_available)
SELECT n, ELT(1 + MOD(n-1, 8), 'A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'), 5 + MOD(n*13, 60)
FROM _numbers WHERE n <= 8;

CREATE TABLE vaccines (
  id INT PRIMARY KEY,
  vaccine_name VARCHAR(50),
  doses_required INT
);
INSERT INTO vaccines (id, vaccine_name, doses_required)
SELECT n, ELT(1 + MOD(n-1, 20), 'BCG', 'Hepatitis B', 'Polio', 'DTP', 'MMR', 'Typhoid', 'Influenza', 'Covishield', 'Covaxin', 'HPV', 'Rabies', 'Tetanus', 'Varicella', 'Hepatitis A', 'Pneumococcal', 'Rotavirus', 'Meningococcal', 'Cholera', 'Yellow Fever', 'Japanese Encephalitis'), 1 + MOD(n, 3)
FROM _numbers WHERE n <= 20;

CREATE TABLE vaccinations (
  id INT PRIMARY KEY,
  patient_id INT,
  vaccine_id INT,
  dose_number INT,
  given_on DATE,
  FOREIGN KEY (patient_id) REFERENCES patients(id),
  FOREIGN KEY (vaccine_id) REFERENCES vaccines(id)
);
INSERT INTO vaccinations (id, patient_id, vaccine_id, dose_number, given_on)
SELECT n, 1 + MOD(n*37, 500), 1 + MOD(n*7, 20), 1 + MOD(n, 3), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY)
FROM _numbers WHERE n <= 900;

CREATE TABLE allergies (
  id INT PRIMARY KEY,
  allergen_name VARCHAR(50)
);
INSERT INTO allergies (id, allergen_name)
SELECT n, CONCAT(ELT(1 + MOD(n-1, 10), 'Penicillin', 'Peanuts', 'Dust', 'Pollen', 'Latex', 'Shellfish', 'Sulfa drugs', 'Eggs', 'Milk', 'Aspirin'), IF(n > 10, CONCAT(' (', n, ')'), ''))
FROM _numbers WHERE n <= 30;

CREATE TABLE patient_allergies (
  id INT PRIMARY KEY,
  patient_id INT,
  allergy_id INT,
  severity VARCHAR(10),
  FOREIGN KEY (patient_id) REFERENCES patients(id),
  FOREIGN KEY (allergy_id) REFERENCES allergies(id)
);
INSERT INTO patient_allergies (id, patient_id, allergy_id, severity)
SELECT n, 1 + MOD(n*41, 500), 1 + MOD(n*7, 30), ELT(1 + MOD(n, 3), 'Mild', 'Moderate', 'Severe')
FROM _numbers WHERE n <= 400;

CREATE TABLE equipment (
  id INT PRIMARY KEY,
  equipment_name VARCHAR(60),
  dept_id INT,
  purchase_date DATE,
  purchase_cost DECIMAL(12,2),
  FOREIGN KEY (dept_id) REFERENCES departments(id)
);
INSERT INTO equipment (id, equipment_name, dept_id, purchase_date, purchase_cost)
SELECT n, CONCAT(ELT(1 + MOD(n, 8), 'ECG Machine', 'Ventilator', 'X-Ray Unit', 'MRI Scanner', 'Defibrillator', 'Infusion Pump', 'Ultrasound', 'Patient Monitor'), ' #', n), 1 + MOD(n*13, 20), DATE_ADD('2015-01-01', INTERVAL MOD(n*13, 3000) DAY), ROUND(20000 + MOD(n*37, 900000) + MOD(n, 100) / 100, 2)
FROM _numbers WHERE n <= 150;

CREATE TABLE equipment_maintenance (
  id INT PRIMARY KEY,
  equipment_id INT,
  maintenance_date DATE,
  cost DECIMAL(10,2),
  technician VARCHAR(80),
  FOREIGN KEY (equipment_id) REFERENCES equipment(id)
);
INSERT INTO equipment_maintenance (id, equipment_id, maintenance_date, cost, technician)
SELECT n, 1 + MOD(n*7, 150), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY), ROUND(500 + MOD(n*37, 20000) + MOD(n, 100) / 100, 2), CONCAT(ELT(1 + MOD(n*43, 20), 'Aarav', 'Priya', 'Rohan', 'Ananya', 'Vikram', 'Sneha', 'Arjun', 'Kavya', 'Rahul', 'Isha', 'Karan', 'Meera', 'Aditya', 'Pooja', 'Nikhil', 'Riya', 'Siddharth', 'Neha', 'Varun', 'Diya'), ' ', ELT(1 + MOD(n*43*7+3, 20), 'Sharma', 'Verma', 'Patel', 'Iyer', 'Reddy', 'Nair', 'Gupta', 'Mehta', 'Joshi', 'Rao', 'Singh', 'Das', 'Kapoor', 'Malhotra', 'Bose', 'Pillai', 'Chopra', 'Kulkarni', 'Menon', 'Saxena'))
FROM _numbers WHERE n <= 500;

CREATE TABLE nurse_shifts (
  id INT PRIMARY KEY,
  nurse_id INT,
  ward_id INT,
  shift_date DATE,
  shift_type VARCHAR(10),
  FOREIGN KEY (nurse_id) REFERENCES nurses(id),
  FOREIGN KEY (ward_id) REFERENCES wards(id)
);
INSERT INTO nurse_shifts (id, nurse_id, ward_id, shift_date, shift_type)
SELECT n, 1 + MOD(n*7, 80), 1 + MOD(n*7, 25), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY), ELT(1 + MOD(n, 3), 'Morning', 'Evening', 'Night')
FROM _numbers WHERE n <= 2000;

CREATE TABLE training_courses (
  id INT PRIMARY KEY,
  course_name VARCHAR(60),
  duration_hours INT
);
INSERT INTO training_courses (id, course_name, duration_hours)
SELECT n, CONCAT(ELT(1 + MOD(n-1, 5), 'Basic Life Support', 'Infection Control', 'Fire Safety', 'Patient Communication', 'Medication Safety'), ' level ', 1 + FLOOR((n-1) / 5)), 2 + MOD(n*3, 20)
FROM _numbers WHERE n <= 25;

CREATE TABLE staff_training (
  id INT PRIMARY KEY,
  nurse_id INT,
  course_id INT,
  completed_on DATE,
  score INT,
  FOREIGN KEY (nurse_id) REFERENCES nurses(id),
  FOREIGN KEY (course_id) REFERENCES training_courses(id)
);
INSERT INTO staff_training (id, nurse_id, course_id, completed_on, score)
SELECT n, 1 + MOD(n*3, 80), 1 + MOD(n*7, 25), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY), 50 + MOD(n*7, 51)
FROM _numbers WHERE n <= 400;

CREATE TABLE meal_plans (
  id INT PRIMARY KEY,
  plan_name VARCHAR(40),
  calories INT
);
INSERT INTO meal_plans (id, plan_name, calories)
SELECT n, ELT(1 + MOD(n-1, 12), 'Regular', 'Diabetic', 'Low sodium', 'Liquid', 'Soft', 'High protein', 'Renal', 'Cardiac', 'Gluten free', 'Vegan', 'Pediatric', 'Post-surgery'), 1200 + MOD(n*150, 1500)
FROM _numbers WHERE n <= 12;

CREATE TABLE meal_requests (
  id INT PRIMARY KEY,
  admission_id INT,
  meal_plan_id INT,
  request_date DATE,
  FOREIGN KEY (admission_id) REFERENCES admissions(id),
  FOREIGN KEY (meal_plan_id) REFERENCES meal_plans(id)
);
INSERT INTO meal_requests (id, admission_id, meal_plan_id, request_date)
SELECT n, 1 + MOD(n*11, 600), 1 + MOD(n*7, 12), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY)
FROM _numbers WHERE n <= 1500;

CREATE TABLE visitor_logs (
  id INT PRIMARY KEY,
  patient_id INT,
  visitor_name VARCHAR(80),
  relation VARCHAR(20),
  visit_date DATE,
  FOREIGN KEY (patient_id) REFERENCES patients(id)
);
INSERT INTO visitor_logs (id, patient_id, visitor_name, relation, visit_date)
SELECT n, 1 + MOD(n*43, 500), CONCAT(ELT(1 + MOD(n*47, 20), 'Aarav', 'Priya', 'Rohan', 'Ananya', 'Vikram', 'Sneha', 'Arjun', 'Kavya', 'Rahul', 'Isha', 'Karan', 'Meera', 'Aditya', 'Pooja', 'Nikhil', 'Riya', 'Siddharth', 'Neha', 'Varun', 'Diya'), ' ', ELT(1 + MOD(n*47*7+3, 20), 'Sharma', 'Verma', 'Patel', 'Iyer', 'Reddy', 'Nair', 'Gupta', 'Mehta', 'Joshi', 'Rao', 'Singh', 'Das', 'Kapoor', 'Malhotra', 'Bose', 'Pillai', 'Chopra', 'Kulkarni', 'Menon', 'Saxena')), ELT(1 + MOD(n, 5), 'Parent', 'Spouse', 'Child', 'Sibling', 'Friend'), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY)
FROM _numbers WHERE n <= 2500;

CREATE TABLE patient_feedback (
  id INT PRIMARY KEY,
  patient_id INT,
  doctor_id INT,
  rating INT,
  comment VARCHAR(60),
  submitted_on DATE,
  FOREIGN KEY (patient_id) REFERENCES patients(id),
  FOREIGN KEY (doctor_id) REFERENCES doctors(id)
);
INSERT INTO patient_feedback (id, patient_id, doctor_id, rating, comment, submitted_on)
SELECT n, 1 + MOD(n*47, 500), 1 + MOD(n*17, 60), 1 + MOD(n*3, 5), ELT(1 + MOD(n, 5), 'Very helpful', 'Long waiting time', 'Excellent care', 'Average', 'Friendly staff'), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY)
FROM _numbers WHERE n <= 800;

CREATE TABLE complaints (
  id INT PRIMARY KEY,
  patient_id INT,
  dept_id INT,
  category VARCHAR(30),
  raised_on DATE,
  resolved VARCHAR(5),
  FOREIGN KEY (patient_id) REFERENCES patients(id),
  FOREIGN KEY (dept_id) REFERENCES departments(id)
);
INSERT INTO complaints (id, patient_id, dept_id, category, raised_on, resolved)
SELECT n, 1 + MOD(n*53, 500), 1 + MOD(n*7, 20), ELT(1 + MOD(n, 5), 'Billing', 'Hygiene', 'Staff behaviour', 'Waiting time', 'Food'), DATE_ADD('2023-01-01', INTERVAL MOD(n*13, 700) DAY), ELT(1 + MOD(n, 3), 'Yes', 'Yes', 'No')
FROM _numbers WHERE n <= 200;

DROP TABLE _numbers;
DROP TABLE _digits;

SELECT COUNT(*) AS tables_created FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'city_hospital';
