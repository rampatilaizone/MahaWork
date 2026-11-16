import os
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import UniqueConstraint, Index
app=Flask(__name__); app.config['SECRET_KEY']=os.getenv('SECRET_KEY','local-dev-change-this-secret')
u=os.getenv('DATABASE_URL','sqlite:///mahawork_local.db')
if u.startswith('postgres://'): u=u.replace('postgres://','postgresql+psycopg://',1)
elif u.startswith('postgresql://') and '+psycopg' not in u: u=u.replace('postgresql://','postgresql+psycopg://',1)
if os.getenv('APP_ENV')=='production' and u.startswith('sqlite'): raise RuntimeError('Production requires PostgreSQL DATABASE_URL')
app.config.update(SQLALCHEMY_DATABASE_URI=u,SQLALCHEMY_TRACK_MODIFICATIONS=False,SQLALCHEMY_ENGINE_OPTIONS={'pool_pre_ping':True},SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.getenv('APP_ENV')=='production',MAX_CONTENT_LENGTH=2*1024*1024)
db=SQLAlchemy(app); csrf=CSRFProtect(app)
SKILLED=['गवंडी / Mason','Steel Fixer / Bar Bender','Carpenter / सुतार','Centering / Shuttering','Plumber / प्लंबर','Electrician / इलेक्ट्रिशियन','Painter / रंगारी','Tiles Fitter','Waterproofing Worker','Welder','Fabricator','POP / Gypsum Worker','Machine Operator','Site Supervisor','Civil Engineer','Other Construction Skill']
UNSKILLED=['General Helper / सामान्य मजूर','Loading-Unloading','Site Cleaning','Construction Labour']; CATEGORIES=['Residential Building','Commercial Building','Infrastructure','Renovation','Waterproofing','Plumbing','Electrical','Other Construction']
class District(db.Model):
 code=db.Column(db.String(20),primary_key=True); name_en=db.Column(db.String(120),nullable=False); name_mr=db.Column(db.String(120),nullable=False)
class Taluka(db.Model):
 code=db.Column(db.String(20),primary_key=True); district_code=db.Column(db.String(20),db.ForeignKey('district.code'),nullable=False,index=True); name_en=db.Column(db.String(120),nullable=False); name_mr=db.Column(db.String(120),nullable=False)
class Village(db.Model):
 code=db.Column(db.String(20),primary_key=True); district_code=db.Column(db.String(20),db.ForeignKey('district.code'),nullable=False,index=True); taluka_code=db.Column(db.String(20),db.ForeignKey('taluka.code'),nullable=False,index=True); name_en=db.Column(db.String(150),nullable=False); name_mr=db.Column(db.String(150),nullable=False)
class User(db.Model):
 id=db.Column(db.Integer,primary_key=True); full_name=db.Column(db.String(140),nullable=False); phone=db.Column(db.String(10),unique=True,nullable=False,index=True); password_hash=db.Column(db.String(255),nullable=False); role=db.Column(db.String(30),nullable=False,index=True); active=db.Column(db.Boolean,default=True,nullable=False); district_code=db.Column(db.String(20),db.ForeignKey('district.code')); taluka_code=db.Column(db.String(20),db.ForeignKey('taluka.code')); village_code=db.Column(db.String(20),db.ForeignKey('village.code')); created_at=db.Column(db.DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class WorkerProfile(db.Model):
 id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey('user.id',ondelete='CASCADE'),unique=True,nullable=False); worker_type=db.Column(db.String(20),nullable=False); skill=db.Column(db.String(140),nullable=False); experience_years=db.Column(db.Integer,default=0); expected_daily_wage=db.Column(db.Integer); availability=db.Column(db.String(25),default='Available'); notes=db.Column(db.Text)
class Job(db.Model):
 id=db.Column(db.Integer,primary_key=True); employer_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False,index=True); title=db.Column(db.String(180),nullable=False); category=db.Column(db.String(80),nullable=False); description=db.Column(db.Text); worker_type=db.Column(db.String(20),nullable=False); skill=db.Column(db.String(140),nullable=False); workers_needed=db.Column(db.Integer,default=1); daily_wage=db.Column(db.Integer); district_code=db.Column(db.String(20),db.ForeignKey('district.code'),nullable=False,index=True); taluka_code=db.Column(db.String(20),db.ForeignKey('taluka.code'),nullable=False,index=True); village_code=db.Column(db.String(20),db.ForeignKey('village.code'),nullable=False,index=True); start_date=db.Column(db.Date); contact_phone=db.Column(db.String(10),nullable=False); status=db.Column(db.String(20),default='Open',index=True); created_at=db.Column(db.DateTime(timezone=True),default=lambda:datetime.now(timezone.utc)); __table_args__=(Index('ix_job_location_status','district_code','taluka_code','village_code','status'),)
class Application(db.Model):
 id=db.Column(db.Integer,primary_key=True); job_id=db.Column(db.Integer,db.ForeignKey('job.id',ondelete='CASCADE'),nullable=False); worker_id=db.Column(db.Integer,db.ForeignKey('user.id',ondelete='CASCADE'),nullable=False); message=db.Column(db.Text); status=db.Column(db.String(20),default='Applied'); created_at=db.Column(db.DateTime(timezone=True),default=lambda:datetime.now(timezone.utc)); __table_args__=(UniqueConstraint('job_id','worker_id',name='uq_job_worker'),)
class AuditLog(db.Model):
 id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey('user.id')); action=db.Column(db.String(100),nullable=False); details=db.Column(db.String(400)); created_at=db.Column(db.DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
def me(): return db.session.get(User,session['uid']) if session.get('uid') else None
def login_required(fn):
 @wraps(fn)
 def w(*a,**k):
  x=me()
  if not x or not x.active: session.clear(); flash('कृपया लॉगिन करा.','warning'); return redirect(url_for('login'))
  return fn(*a,**k)
 return w
def roles(*allowed):
 def deco(fn):
  @login_required
  @wraps(fn)
  def w(*a,**k):
   if me().role not in allowed: abort(403)
   return fn(*a,**k)
  return w
 return deco
def valid_place(d,t,v): return bool(District.query.filter_by(code=d).first() and Taluka.query.filter_by(code=t,district_code=d).first() and Village.query.filter_by(code=v,taluka_code=t,district_code=d).first())
def audit(a,d=''):
 if session.get('uid'): db.session.add(AuditLog(user_id=session['uid'],action=a,details=d[:400]))
@app.context_processor
def globals_(): return dict(me=me(),districts=District.query.order_by(District.name_mr).all(),skilled=SKILLED,unskilled=UNSKILLED,categories=CATEGORIES)
@app.get('/')
def home():
 q=Job.query.filter_by(status='Open')
 for k,col in [('district','district_code'),('taluka','taluka_code'),('village','village_code'),('worker_type','worker_type'),('skill','skill')]:
  if request.args.get(k): q=q.filter(getattr(Job,col)==request.args[k])
 jobs=q.order_by(Job.created_at.desc()).limit(100).all(); stats={'Workers':User.query.filter_by(role='Worker').count(),'Employers':User.query.filter(User.role.in_(['Builder','Contractor'])).count(),'Open Jobs':Job.query.filter_by(status='Open').count(),'Applications':Application.query.count()}
 return render_template('home.html',jobs=jobs,stats=stats)
@app.route('/register/worker',methods=['GET','POST'])
def register_worker():
 if request.method=='POST':
  f=request.form; p=f.get('phone','').strip(); typ=f.get('worker_type'); skill=f.get('skill'); good=(typ=='Skilled' and skill in SKILLED) or (typ=='Unskilled' and skill in UNSKILLED)
  if not f.get('full_name','').strip() or not p.isdigit() or len(p)!=10 or len(f.get('password',''))<8 or not good or not valid_place(f.get('district_code'),f.get('taluka_code'),f.get('village_code')): flash('नाव, 10 अंकी मोबाईल, 8+ अक्षरांचा पासवर्ड, कौशल्य आणि योग्य गाव तपासा.','danger')
  elif User.query.filter_by(phone=p).first(): flash('हा मोबाईल आधी नोंदणीकृत आहे.','danger')
  else:
   x=User(full_name=f['full_name'].strip(),phone=p,password_hash=generate_password_hash(f['password']),role='Worker',district_code=f['district_code'],taluka_code=f['taluka_code'],village_code=f['village_code']); db.session.add(x); db.session.flush(); db.session.add(WorkerProfile(user_id=x.id,worker_type=typ,skill=skill,experience_years=int(f.get('experience_years') or 0),expected_daily_wage=int(f.get('expected_daily_wage') or 0),availability=f.get('availability','Available'),notes=f.get('notes',''))); db.session.commit(); flash('कामगार नोंदणी पूर्ण. Login करा.','success'); return redirect(url_for('login'))
 return render_template('worker_register.html')
@app.route('/register/employer',methods=['GET','POST'])
def register_employer():
 if request.method=='POST':
  f=request.form;p=f.get('phone','').strip();r=f.get('role')
  if not f.get('full_name','').strip() or not p.isdigit() or len(p)!=10 or len(f.get('password',''))<8 or r not in ('Builder','Contractor'): flash('नाव, 10 अंकी मोबाईल, भूमिका व 8+ अक्षरांचा पासवर्ड भरा.','danger')
  elif User.query.filter_by(phone=p).first(): flash('हा मोबाईल आधी नोंदणीकृत आहे.','danger')
  else: db.session.add(User(full_name=f['full_name'],phone=p,password_hash=generate_password_hash(f['password']),role=r));db.session.commit();flash('नोंदणी पूर्ण. Login करा.','success');return redirect(url_for('login'))
 return render_template('employer_register.html')
@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  x=User.query.filter_by(phone=request.form.get('phone','').strip()).first()
  if x and x.active and check_password_hash(x.password_hash,request.form.get('password','')): session.clear();session['uid']=x.id;audit('login');db.session.commit();return redirect(url_for('dashboard'))
  flash('मोबाईल किंवा पासवर्ड चुकीचा.','danger')
 return render_template('login.html')
@app.get('/logout')
def logout(): session.clear();return redirect(url_for('home'))
@app.get('/dashboard')
@login_required
def dashboard(): return redirect(url_for('admin') if me().role in ('Super Admin','District Admin') else url_for('employer') if me().role in ('Builder','Contractor') else url_for('worker'))
@app.get('/worker')
@roles('Worker')
def worker(): return render_template('worker.html',apps=Application.query.filter_by(worker_id=me().id).order_by(Application.created_at.desc()).all())
@app.get('/employer')
@roles('Builder','Contractor')
def employer(): return render_template('employer.html',jobs=Job.query.filter_by(employer_id=me().id).order_by(Job.created_at.desc()).all())
@app.route('/jobs/new',methods=['GET','POST'])
@roles('Builder','Contractor')
def new_job():
 if request.method=='POST':
  f=request.form
  if not all(f.get(k) for k in ['title','category','worker_type','skill','district_code','taluka_code','village_code','contact_phone']) or not valid_place(f.get('district_code'),f.get('taluka_code'),f.get('village_code')): flash('सर्व माहिती व योग्य ठिकाण निवडा.','danger')
  elif f['worker_type'] not in ('Skilled','Unskilled') or not f['contact_phone'].isdigit() or len(f['contact_phone'])!=10: flash('कामगार प्रकार किंवा मोबाईल चुकीचा.','danger')
  else:
   from datetime import date
   j=Job(employer_id=me().id,title=f['title'],category=f['category'],description=f.get('description',''),worker_type=f['worker_type'],skill=f['skill'],workers_needed=max(1,int(f.get('workers_needed') or 1)),daily_wage=int(f.get('daily_wage') or 0),district_code=f['district_code'],taluka_code=f['taluka_code'],village_code=f['village_code'],start_date=date.fromisoformat(f['start_date']) if f.get('start_date') else None,contact_phone=f['contact_phone']);db.session.add(j);db.session.flush();audit('job_created',str(j.id));db.session.commit();flash('काम प्रकाशित झाले.','success');return redirect(url_for('employer'))
 return render_template('job_form.html')
@app.post('/jobs/<int:jid>/apply')
@roles('Worker')
def apply(jid):
 j=db.session.get(Job,jid)
 if not j or j.status!='Open': abort(404)
 if Application.query.filter_by(job_id=jid,worker_id=me().id).first(): flash('या कामासाठी आधी अर्ज केला आहे.','warning')
 else: db.session.add(Application(job_id=jid,worker_id=me().id,message=request.form.get('message','')));audit('job_applied',str(jid));db.session.commit();flash('अर्ज पाठवला.','success')
 return redirect(url_for('worker'))
@app.get('/applications')
@roles('Builder','Contractor')
def applications():
 ids=[j.id for j in Job.query.filter_by(employer_id=me().id).all()]; rows=Application.query.filter(Application.job_id.in_(ids)).order_by(Application.created_at.desc()).all() if ids else [];return render_template('applications.html',rows=rows)
@app.post('/applications/<int:aid>/status')
@roles('Builder','Contractor','District Admin','Super Admin')
def app_status(aid):
 a=db.session.get(Application,aid)
 if not a: abort(404)
 j=db.session.get(Job,a.job_id)
 if me().role not in ('District Admin','Super Admin') and j.employer_id!=me().id: abort(403)
 s=request.form.get('status')
 if s not in ('Applied','Shortlisted','Selected','Rejected'): abort(400)
 a.status=s;audit('application_status',f'{aid}:{s}');db.session.commit();return redirect(url_for('applications'))
@app.get('/admin')
@roles('District Admin','Super Admin')
def admin():
 counts={'Workers':User.query.filter_by(role='Worker').count(),'Builders':User.query.filter_by(role='Builder').count(),'Contractors':User.query.filter_by(role='Contractor').count(),'Jobs':Job.query.count(),'Applications':Application.query.count(),'Districts':District.query.count(),'Talukas':Taluka.query.count(),'Villages':Village.query.count()};return render_template('admin.html',counts=counts,users=User.query.order_by(User.created_at.desc()).limit(100).all())
@app.get('/api/locations/districts')
def districts(): return jsonify([{'code':x.code,'en':x.name_en,'mr':x.name_mr} for x in District.query.order_by(District.name_mr)])
@app.get('/api/locations/talukas')
def talukas(): return jsonify([{'code':x.code,'en':x.name_en,'mr':x.name_mr} for x in Taluka.query.filter_by(district_code=request.args.get('district')).order_by(Taluka.name_mr)])
@app.get('/api/locations/villages')
def villages(): return jsonify([{'code':x.code,'en':x.name_en,'mr':x.name_mr} for x in Village.query.filter_by(district_code=request.args.get('district'),taluka_code=request.args.get('taluka')).order_by(Village.name_mr)])
@app.get('/health')
def health():
 try: db.session.execute(db.select(District));return jsonify(status='ok',database='connected')
 except Exception:return jsonify(status='error',database='unavailable'),503
@app.cli.command('init-db')
def init_db():
 db.create_all();p=os.getenv('SUPER_ADMIN_PHONE','').strip();pw=os.getenv('SUPER_ADMIN_PASSWORD','')
 if p and pw and not User.query.filter_by(phone=p).first(): db.session.add(User(full_name=os.getenv('SUPER_ADMIN_NAME','MahaWork Super Admin'),phone=p,password_hash=generate_password_hash(pw),role='Super Admin'));db.session.commit()
 print('Database tables ready.')
@app.cli.command('import-locations-csv')
def import_locations_csv():
 import csv
 with open(os.getenv('LOCATIONS_CSV','maharashtra_locations.csv'),encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f):
   d=db.session.get(District,r['district_code']) or District(code=r['district_code'],name_en=r['district_en'],name_mr=r['district_mr']);d.name_en,d.name_mr=r['district_en'],r['district_mr']
   t=db.session.get(Taluka,r['taluka_code']) or Taluka(code=r['taluka_code'],district_code=r['district_code'],name_en=r['taluka_en'],name_mr=r['taluka_mr']);t.district_code,t.name_en,t.name_mr=r['district_code'],r['taluka_en'],r['taluka_mr']
   v=db.session.get(Village,r['village_code']) or Village(code=r['village_code'],district_code=r['district_code'],taluka_code=r['taluka_code'],name_en=r['village_en'],name_mr=r['village_mr']);v.district_code,v.taluka_code,v.name_en,v.name_mr=r['district_code'],r['taluka_code'],r['village_en'],r['village_mr'];db.session.add_all([d,t,v])
 db.session.commit();print('Location data imported.')
@app.errorhandler(403)
def forbidden(_): return render_template('message.html',title='प्रवेश नाकारला',message='या पानासाठी परवानगी नाही.'),403
@app.errorhandler(404)
def missing(_): return render_template('message.html',title='पान सापडले नाही',message='हे पान उपलब्ध नाही.'),404
with app.app_context():
 db.create_all();p=os.getenv('SUPER_ADMIN_PHONE','').strip();pw=os.getenv('SUPER_ADMIN_PASSWORD','')
 if p and pw and not User.query.filter_by(phone=p).first(): db.session.add(User(full_name=os.getenv('SUPER_ADMIN_NAME','MahaWork Super Admin'),phone=p,password_hash=generate_password_hash(pw),role='Super Admin'));db.session.commit()
if __name__=='__main__': app.run(host='127.0.0.1',port=int(os.getenv('PORT','5000')),debug=False)
