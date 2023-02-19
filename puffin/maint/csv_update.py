#! /usr/bin/python
from slugify import slugify
from puffin.db.database import init_db, db_session
from puffin.db.model import *
from werkzeug.security import check_password_hash, generate_password_hash


def update_from_uib(session, row, course):
    """Create or update user and uib/mitt_uib accounts from Mitt UiB data."""
    name = row['sortable_name']
    (lastname, firstname) = [s.strip() for s in name.split(',', 1)]
    # get or create UiB user (has login name as user name)
    uib_user = get_or_define(session, Account, {'username': row['login_id'], 'provider_id': providers['uib']},
                             {'ref_id': int(row['id']), 'email': row['email'], 'fullname': name})
    # get or create Mitt UiB user (has Canvas id as user name)
    # mitt_uib_user = get_or_define(session, Account, {'username': row['id'], 'provider_id': providers['mitt_uib']}, {
    #                              'email': row['email'], 'fullname': name})
    # create User object if necessary

    if uib_user.user == None:
        user = User(firstname=firstname, lastname=lastname)
        uib_user.user = user
    else:
        user = uib_user.user
    session.add_all([user, uib_user])
    session.commit()
    print(user)
    # name changed?
    if uib_user.fullname != name:
        # session.add(user)
        user.firstname = firstname
        user.lastname = lastname
        uib_user.fullname = name
    # update data
    user.email = uib_user.email = row['email']
    uib_user.avatar_url = row['avatar_url']
    if course != None:
        role = roles.get(row['role'], row['role'])
        enrollment = get_or_define(session, Enrollment, {
                                   'course': course, 'user': user}, {'role': role})
        session.add(enrollment)

    if row['gituser'] and row['gitid']:
        gitid = int(row['gitid'])
        git_user = get_or_define(session, Account, {'username': row['gituser'],
                                                    'provider_id': providers['git.app.uib.no']}, {'user_id': user.id, 'ref_id': gitid, 'fullname': name})
        session.add(git_user)


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
