#! /usr/bin/python
import csv
from slugify import slugify
from sqlalchemy import select
from puffin.db.database import init, db_session
from puffin.db.model_tables import  Assignment, User, Account, Course
from puffin.db.model_util import update_from_uib, get_or_define
from puffin.app.app import app
import re

def url_to_project_path(url):
    if url != None:
        url = re.sub('^https://git.app.uib.no/', '', url)
        url = re.sub('/-/.*$','',url)
    return url

if __name__ == '__main__':
    init(app)

    inf226, added = get_or_define(db_session, Course, {'external_id': 42576}, {
        'name': 'INF226 23H', 'slug':slugify('INF226 23H')})
    db_session.add(inf226)
    db_session.commit()
    filename = '/home/anya/inf226/admin/students.csv'
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            update_from_uib(db_session, row, inf226)
            db_session.commit()

    user = db_session.execute(select(User).where(Account.user_id==User.id,Account.username=='Anya.Bagge')).scalar_one()
    print(user)
    db_session.commit()

    asgn, added = get_or_define(db_session, Assignment, {'course_id':inf226.id})
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
