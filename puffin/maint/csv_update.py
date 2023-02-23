#! /usr/bin/python
from slugify import slugify
from puffin.db.database import init_db, db_session
from puffin.db.model import *
from werkzeug.security import check_password_hash, generate_password_hash




if __name__ == '__main__':
    init_db()

    inf112 = get_or_define(db_session, Course, {'id': 39903}, {
        'name': 'INF112 23V', 'slug':slugify('INF112 23V')})
    db_session.add(inf112)
    inf222 = get_or_define(db_session, Course, {'id': 39786}, {
                           'name': 'INF222 23V', 'slug':slugify('INF222 23V')})
    db_session.add(inf222)
    db_session.commit()
    filename = '../canvas-users.csv'
    filename = '../canvas-users_inf112_2023-01-19.csv'
    filename = '/home/anya/inf222/test-runner/students.csv'
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            update_from_uib(db_session, row, inf222)
            db_session.commit()

    user = db_session.execute(select(User).where(Account.user_id==User.id,Account.username=='Anya.Bagge')).scalar_one()
    user.password = generate_password_hash('abc123')
    db_session.commit()
    if False:
        course_id = 39903
        course = db_session.execute(select(Course).filter_by(
            id=course_id)).scalar_one_or_none()
        if course == None:
            raise Exception(f'No such course: {course_id}')
        users = db_session.execute(select(User).join(User.enrollments).filter_by(
            course=course).order_by(User.lastname)).scalars().all()
        for u in users:
            jsonu = u.to_json()
            enr = u.enrollment(course_id)
            jsonu['role'] = enr.role
            print(jsonu)
        group = Group(name='Group1', slug='group_1', kind='team',
                    course_id=course_id, external_id="1234")
        db_session.add(group)
        db_session.commit()
