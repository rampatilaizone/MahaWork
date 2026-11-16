MAHAWORK MULTI-USER CLOUD SOFTWARE – V1

या आवृत्तीत Worker, Builder, Contractor, District Admin आणि Super Admin साठी स्वतंत्र Login, एकच shared PostgreSQL database, Skilled/Unskilled registration, construction job posting, worker applications, employer application status, Admin dashboard, audit log आणि District/Taluka/Village cascading API आहेत.

LOCAL WINDOWS TEST:
1) Python 3.12 किंवा 3.13 शिफारसीय (Python 3.15 वर dependency compatibility तपासा).
2) या folder मध्ये CMD उघडा.
3) py -m venv .venv
4) .venv\Scripts\activate
5) pip install -r requirements.txt
6) set SECRET_KEY=your-long-random-secret
7) py -m flask --app app init-db
8) py -m flask --app app run
9) Browser: http://127.0.0.1:5000

Local test साठी SQLite वापरले जाईल. हा database फक्त तुमच्या PC वर आहे; इतर लोकांना online वापरता येण्यासाठी PostgreSQL cloud hosting आवश्यक आहे.

CLOUD DEPLOYMENT:
1) GitHub repository तयार करून हा folder upload करा.
2) Render वर New > Blueprint करून repository connect करा.
3) render.yaml मधील PostgreSQL + Web service deploy करा.
4) SUPER_ADMIN_PHONE आणि SUPER_ADMIN_PASSWORD secrets भरा.
5) Deploy नंतर /health तपासा; database connected दिसणे आवश्यक.
6) नंतर domain खरेदी करून hosting मध्ये custom domain जोडा.

LOCATION MASTER:
District/Taluka/Village data रिकामा आहे. अधिकृत LGD source मधील codes आणि names वापरून maharashtra_locations.csv भरा. Columns: district_code,district_en,district_mr,taluka_code,taluka_en,taluka_mr,village_code,village_en,village_mr
Import: set LOCATIONS_CSV=maharashtra_locations.csv नंतर py -m flask --app app import-locations-csv

महत्त्वाचे: ही Cloud-ready MVP codebase आहे; ती अद्याप public internet वर deploy झालेली नाही. OTP verification, password reset, file storage, worker consent/privacy policy, district-admin district-level restrictions, backups/restore आणि live security testing हे public launch पूर्वी करणे आवश्यक आहे. सध्या District Admin role dashboard access देतो; जिल्हा-निहाय data restriction पुढील security phase मध्ये implement करणे आवश्यक.
