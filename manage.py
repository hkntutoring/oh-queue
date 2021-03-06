#!/usr/bin/env python3
import datetime
import functools
import random
import sys

import alembic
import names

from alembic.config import Config
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from oh_queue import app, socketio
from oh_queue.models import Group, GroupAttendance, GroupAttendanceStatus, GroupStatus, db, Assignment, ConfigEntry, \
    Location, Ticket, \
    TicketStatus, User, \
    Appointment, \
    AppointmentSignup, AppointmentStatus

migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)

alembic_cfg = Config('migrations/alembic.ini')


def not_in_production(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if app.config.get('ENV') == 'prod':
            print('this commend should not be run in production. Aborting')
            sys.exit(1)
        return f(*args, **kwargs)

    return wrapper


@manager.command
@not_in_production
def seed_data():
    print('Seeding...')

    assignments = [Assignment(name=name, course="HKN", visible=True) for name in ['Hog', 'Maps', 'Ants', 'Scheme']]
    locations = [Location(name=name, course="HKN", visible=True, online=True, link="") for name in
                 ['Online']]
    questions = list(range(1, 16)) + ['Other', 'EC', 'Checkoff']
    descriptions = ['', 'I\'m in the hallway', 'SyntaxError on Line 5']

    students = []

    for i in range(50):
        real_name = names.get_full_name()
        first_name, last_name = real_name.lower().split(' ')
        email = '{0}{1}@{2}'.format(
            random.choice([first_name, first_name[0]]),
            random.choice([last_name, last_name[0]]),
            random.choice(['berkeley.edu', 'gmail.com']),
        )
        student = User.query.filter_by(email=email).one_or_none()
        if not student:
            student = User(name=real_name, email=email, course="ok")
            students.append(student)
            db.session.add(student)
            db.session.commit()

        delta = datetime.timedelta(minutes=random.randrange(0, 30))
        ticket = Ticket(
            user=student,
            status=TicketStatus.pending,
            created=datetime.datetime.utcnow() - delta,
            assignment=random.choice(assignments),
            location=random.choice(locations),
            question=random.choice(questions),
            description=random.choice(descriptions),
            course="HKN"
        )
        db.session.add(ticket)

    appointments = [Appointment(
        start_time=datetime.datetime.now() + datetime.timedelta(hours=random.randrange(-8, 50)),
        duration=datetime.timedelta(minutes=random.randrange(30, 120, 30)),
        location=random.choice(locations),
        capacity=5,
        status=AppointmentStatus.pending,
        course="HKN",
        helper=random.choice(students)
    ) for _ in range(70)]

    for assignment in assignments:
        db.session.add(assignment)
    for location in locations:
        db.session.add(location)
    for appointment in appointments:
        db.session.add(appointment)

    db.session.commit()

    signups = [AppointmentSignup(
        appointment=random.choice(appointments),
        user=random.choice(students),
        assignment=random.choice(assignments),
        question=random.choice(questions),
        description=random.choice(descriptions),
        course="HKN",
    ) for _ in range(120)]

    for signup in signups:
        db.session.add(signup)

    db.session.commit()

    groups = [
        Group(
            group_status=GroupStatus.active,
            question=random.choice(questions),
            assignment=random.choice(assignments),
            location=random.choice(locations),
            attendees=[GroupAttendance(
                user=student,
                group_attendance_status=GroupAttendanceStatus.present,
                course="HKN"
            ) for student in random.sample(students, 5)],
            call_url="",
            doc_url="",
            course="HKN",
        ) for _ in range(120)]

    for group in groups:
        db.session.add(group)

    db.session.commit()


@manager.command
@not_in_production
def resetdb():
    print('Dropping tables...')
    db.drop_all(app=app)
    initdb()


@manager.command
def initdb():
    print('Creating tables...')
    db.create_all(app=app)
    print('Stamping DB revision...')
    alembic.command.stamp(alembic_cfg, "head")


@manager.command
@not_in_production
def server():
    #DebugToolbarExtension(app)
    socketio.run(app)
    #socketio.run(app, host=app.config.get('HOST'), port=app.config.get('PORT'))


if __name__ == '__main__':
    manager.run()
