import os
import sys
import pytest
import tempfile
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
o_path = os.getcwd()
sys.path.append(o_path)

import nearbyEvents.models
from nearbyEvents import app
from nearbyEvents.models import User, Event, Area, Country, Reservation, Ticket
import datetime

@pytest.fixture
def db_handle():
    db_fd, db_fname = tempfile.mkstemp()
    config = {
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + db_fname,
        "TESTING": True,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False
    }
    global app
    app = nearbyEvents.create_app(config)
    from nearbyEvents.models import User, Event, Area, Country, Reservation, Ticket
    with app.app_context():
        nearbyEvents.models.db.init_app(app)
        nearbyEvents.models.db.create_all()
        
    yield nearbyEvents.models.db
    
    nearbyEvents.models.db.session.remove()
    os.close(db_fd)
    os.unlink(db_fname)

from sqlalchemy.engine import Engine
from sqlalchemy import event
from nearbyEvents.models import User, Event, Area, Country, Reservation, Ticket

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

def _get_user():
    """Creates a dummy User instance"""
    return User(
        first_name="user",
        last_name="test",
        birth_date=datetime.datetime.now(),
        email="user.test@gmail.com"
        
    )
    
def _get_Country():
    """Creates a dummy Country instance"""
    return Country(
        country="Finland",
        currency="EUR"
    )
    
def _get_Area():
    """Creates a dummy Area instance"""
    return Area(
        name="Oulu - Keskusta"
    )
    
def _get_Event():
    """Creates a dummy Event instance"""
    return Event(
        name="Stand Up Comedy at 45 Special",
        max_tickets=150,
        ticket_price=19,
        status="Cancelled",
        event_begin=datetime.datetime.now() + datetime.timedelta(days = 1)
    )
def _get_Reservation():
    """Creates a dummy Reservation instance"""
    return Reservation(
        paid=True,
        created_at=datetime.datetime.now()
    )
    
def _get_Ticket():
    """Creates a dummy Ticket instance"""
    return Ticket(
        type="VIP"
    )
    
def test_create_instances(db_handle):
    """
    Tests that we can create one instance of each model and save them to the
    database using valid values for all columns. After creation, test that 
    everything can be found from database, and that all relationships have been
    saved correctly.
    """
    with app.app_context():
        # Create everything
        user = _get_user()
        country=_get_Country()
        event=_get_Event()
        area=_get_Area()
        reservation=_get_Reservation()
        ticket=_get_Ticket()
        
        area.in_country=country
        user.country=country
        event.in_area=area
        event.is_managed_by=user
        ticket.in_reservation=reservation
        reservation.user_booked=user
        reservation.for_event=event
        
        db_handle.session.add(user)
        db_handle.session.add(country)
        db_handle.session.add(area)
        db_handle.session.add(event)
        db_handle.session.add(reservation)
        db_handle.session.add(ticket)
        db_handle.session.commit()
        
        # Check that everything exists
        assert User.query.count() == 1
        assert Country.query.count() == 1
        assert Area.query.count() == 1
        assert Event.query.count() == 1
        assert Reservation.query.count() == 1
        assert Ticket.query.count() == 1
        db_user = User.query.first()
        db_country = Country.query.first()
        db_area = Area.query.first()
        db_event = Event.query.first()
        db_reservation = Reservation.query.first()
        db_ticket = Ticket.query.first()
        
        # Check all relationships (both sides)
        assert db_user.country == db_country
        assert db_user in db_country.users
        
        assert db_area.in_country == db_country
        
        assert db_event in db_user.managed_events
        assert db_event.is_managed_by == db_user
        assert db_event.in_area == db_area
        assert db_event in db_area.events
        
        assert db_reservation in db_event.reservations
        assert db_reservation in db_user.reservations
        assert db_reservation.user_booked == db_user
        assert db_reservation.for_event == db_event
        
        assert db_ticket.in_reservation == db_reservation
        assert db_ticket in db_reservation.tickets

def test_user_ondelete_country(db_handle):
    """
    Tests that users's nationality foreign key is set to null when the country
    is deleted.
    """
    with app.app_context():
        # Create instances
        user = _get_user()
        country = _get_Country()
        
        # Create relations
        user.country = country
        
        # Add to database and then delete the relation instance
        db_handle.session.add(user)
        db_handle.session.commit()
        db_handle.session.delete(country)
        db_handle.session.commit()
        
        # See if the ondelete function works as designed
        assert user.nationality is None
    
def test_area_ondelete_country(db_handle):
    """
    Tests that row of the area is deleted when the country
    is deleted.
    """
    with app.app_context():
        # Create instances
        area = _get_Area()
        country = _get_Country()
        
        # Create relations
        area.in_country = country
        # Add to database and then delete the relation instance
        db_handle.session.add(area)
        db_handle.session.commit()
        db_handle.session.delete(country)
        db_handle.session.commit()
        
        # See if the ondelete function works as designed
        assert Area.query.count() == 0
    
def test_event_ondelete_manager(db_handle):
    """
    Tests that the manager is null when the manager
    is deleted.
    """
    with app.app_context():
        # Create instances
        user = _get_user()
        event = _get_Event()
        
        # Create relations
        event.is_managed_by = user
        
        # Add to database
        db_handle.session.add(event)
        db_handle.session.commit()
        
        # See if the relation was correct
        assert event.event_manager == user.id
        
        # delete the relation instance
        db_handle.session.delete(user)
        db_handle.session.commit()
        # See if the ondelete function works as designed
        assert event.event_manager is None
def test_event_ondelete_area(db_handle):
    """
    Tests that the in_area is null when the area
    is deleted.
    """
    with app.app_context():
        # Create instances
        area = _get_Area()
        country = _get_Country()
        event = _get_Event()
        # Create relations
        event.in_area = area
        area.in_country = country
        
        # Add to database
        db_handle.session.add(area)
        db_handle.session.commit()
        
        # See if the relation was correct
        assert event.area_name == area.name
        
        # delete the relation instance
        db_handle.session.delete(area)
        db_handle.session.commit()
        
        # See if the ondelete function works as designed
        assert event.area_name is None

def test_reservation_ondelete_user(db_handle):
    """
    Tests that row of the reservation is deleted when the user
    is deleted.
    """
    with app.app_context():
        # Create instances
        reservation = _get_Reservation()
        area = _get_Area()
        country = _get_Country()
        event = _get_Event()
        user = _get_user()
        
        # Create relations
        area.in_country = country
        event.in_area = area
        reservation.for_event = event
        reservation.user_booked = user
        
        # Add to database and then delete the relation instance
        db_handle.session.add(reservation)
        db_handle.session.commit()
        db_handle.session.delete(user)
        db_handle.session.commit()
        
        # See if the ondelete function works as designed
        assert Reservation.query.count() == 0
    
def test_reservation_ondelete_event(db_handle):
    """
    Tests that row of the reservation is deleted when the event
    is deleted.
    """
    with app.app_context():
        # Create instances
        reservation = _get_Reservation()
        area = _get_Area()
        country = _get_Country()
        event = _get_Event()
        user = _get_user()
        
        # Create relations
        area.in_country = country
        event.in_area = area
        reservation.for_event = event
        reservation.user_booked = user
        
        # Add to database and then delete the relation instance
        db_handle.session.add(reservation)
        db_handle.session.commit()
        db_handle.session.delete(event)
        db_handle.session.commit()
        
        # See if the ondelete function works as designed
        assert Reservation.query.count() == 0
    
def test_ticket_ondelete_reservation(db_handle):
    """
    Tests that row of the ticket is deleted when the reservation
    is deleted.
    """
    with app.app_context():
        # Create instances
        reservation = _get_Reservation()
        area = _get_Area()
        country = _get_Country()
        event = _get_Event()
        user = _get_user()
        ticket = _get_Ticket()
        
        # Create relations
        area.in_country = country
        event.in_area = area
        reservation.for_event = event
        reservation.user_booked = user
        ticket.in_reservation = reservation
        
        # Add to database and then delete the relation instance
        db_handle.session.add(ticket)
        db_handle.session.commit()
        db_handle.session.delete(reservation)
        db_handle.session.commit()
        
        # See if the ondelete function works as designed
        assert Ticket.query.count() == 0
        
def test_IntegrityError_for_models(db_handle):
    """
    Tests integrityError for all classes.
    """
    with app.app_context():
        ticket_1 = _get_Ticket()
        ticket_2 = _get_Ticket()
        db_handle.session.add(ticket_1)
        db_handle.session.add(ticket_2)  
        with pytest.raises(IntegrityError):
            db_handle.session.commit()
            
        db_handle.session.rollback()
        event_1 = _get_Event()
        event_2 = _get_Event()
        db_handle.session.add(event_1)
        db_handle.session.add(event_2)  
        with pytest.raises(IntegrityError):
            db_handle.session.commit()
            
        db_handle.session.rollback()
        area_1 = _get_Area()
        area_2 = _get_Area()
        db_handle.session.add(area_1)
        db_handle.session.add(area_2)  
        with pytest.raises(IntegrityError):
            db_handle.session.commit()

        db_handle.session.rollback()
        user_1 = _get_user()
        user_2 = _get_user()
        db_handle.session.add(user_1)
        db_handle.session.add(user_2)  
        with pytest.raises(IntegrityError):
            db_handle.session.commit()
            
        db_handle.session.rollback()
        country_1 = _get_Country()
        country_2 = _get_Country()
        db_handle.session.add(country_1)
        db_handle.session.add(country_2)  
        with pytest.raises(IntegrityError):
            db_handle.session.commit()
            
        db_handle.session.rollback()
        reservation_1 = _get_Reservation()
        reservation_2 = _get_Reservation()
        db_handle.session.add(reservation_1)
        db_handle.session.add(reservation_2)  
        with pytest.raises(IntegrityError):
            db_handle.session.commit()

def test_ticket_foreignkey_reservation(db_handle):
    """
    Tests foreignkey value for reservation and ticket
    """
    with app.app_context():
        user = _get_user()
        event = _get_Event()
        reservation = _get_Reservation()
        reservation.for_event = event
        reservation.user_booked = user
        ticket = _get_Ticket()
        ticket.in_reservation = reservation

        db_handle.session.add(ticket)
        db_handle.session.commit()
        assert Reservation.query.count() == 1
        assert Ticket.query.count() == 1
        db_reservation = Reservation.query.first()
        db_ticket = Ticket.query.first()
        assert db_ticket.in_reservation == db_reservation
        assert db_ticket in db_reservation.tickets

def test_ticket_onmodify_area(db_handle):
    """
    Tests event.area_name change that is changing also the area.name.
    """
    with app.app_context():
        # Create instances
        reservation = _get_Reservation()
        area = _get_Area()
        country = _get_Country()
        event = _get_Event()
        user = _get_user()
        ticket = _get_Ticket()
        
        # Create relations
        area.in_country = country
        event.in_area = area
        reservation.for_event = event
        reservation.user_booked = user
        ticket.in_reservation = reservation
        
        # Add to database
        db_handle.session.add(ticket)
        db_handle.session.commit()
        
        # Check Addings
        db_event = Event.query.first()
        db_area = Area.query.first()
        db_reservation = Reservation.query.first()
        assert Ticket.query.count() == 1
        assert Area.query.count() == 1
        assert Reservation.query.count() == 1
        assert db_event.in_area == db_area
        assert db_event in db_area.events
        assert db_reservation in db_ticket.in_reservation

        
        #Different Area
        area_new = Area(
        name="Helsinki - Vuosaari"
        )
        country_new = _get_Country()
        country_new.country = "Spain"
        # Set new area name and country
        db_area = Area.query.first()
        db_country = Country.query.first()
        db_area.name = area_new.name
        db_country.country = country_new.country
        db_handle.session.commit()

        # See if the value is modified
        assert Ticket.query.count() == 1
        assert Area.query.count() == 1
        assert Event.query.count() == 1
        assert Country.query.count() == 1
        db_area = Area.query.first()
        db_ticket = Ticket.query.first()
        db_event_updated = Event.query.first()
        db_country_updated = Country.query.first()
        assert db_event_updated.in_area.name == area_new.name
        assert db_event_updated in area.events
        assert db_area.name == db_event_updated.in_area.name
        assert db_area.name == area_new.name
        assert db_area.in_country == db_country_updated.country
        
def test_ticket_onmodify_area(db_handle):
    """
    Tests event.area_name change that is changing also the area.name.
    """
    with app.app_context():
        # Create instances
        reservation = _get_Reservation()
        area = _get_Area()
        country = _get_Country()
        event = _get_Event()
        event_2 = _get_Event()
        event_2.name = "Fifty shades of gray in Valkea"
        user = _get_user()
        user_2 = _get_user()
        user_2.first_name = "Pekka"
        user_2.last_name = "Pouta"
        user_2.email = "pekkispouta@gmail.com"
        ticket = _get_Ticket()
        
        # Create relations
        area.in_country = country
        event.in_area = area
        event.is_managed_by = user
        db_handle.session.add(event)
        db_handle.session.add(event_2)
        db_handle.session.commit()
        

        reservation.for_event = event
        reservation.user_id = user_2.id
        reservation.user_booked = user_2
        ticket.in_reservation = reservation
        
        # Add to database

        db_handle.session.add(ticket)
        db_handle.session.commit()
        
        # Check Addings
        db_event = Event.query.first()
        db_area = Area.query.first()
        db_user = User.query.first()
        db_user_2 = User.query.filter_by(id=2).first()
        db_reservation = Reservation.query.first()
        userid = db_user.id
        assert Event.query.count() == 2
        assert Area.query.count() == 1
        assert User.query.count() == 2
        assert Reservation.query.count() == 1
        assert db_event.in_area == db_area
        assert db_event in db_area.events
        assert userid == db_event.event_manager
        assert db_user_2 == db_reservation.user_booked

        
        # Different user
        new_user = _get_user()
        new_user.first_name="Matti"
        new_user.last_name="Makulainen"
        
        # Set new user to manage event1
        db_user = User.query.first()
        db_user.first_name = new_user.first_name
        db_user.last_name = new_user.last_name
        
        # modify reservation for user_2
        db_reservation = Reservation.query.first()
        db_reservation.event_id = 2
        db_handle.session.commit()

        # See if the value is modified
        assert User.query.count() == 2
        assert Event.query.count() == 2
        assert Reservation.query.count() == 1
        db_user_updated = User.query.filter_by(first_name="Matti").first()
        db_user_2 = User.query.filter_by(first_name="Pekka").first()
        db_event = Event.query.first()
        db_event_2 = Event.query.filter_by(id=2).first()
        db_reservation = Reservation.query.first()
        assert db_event.event_manager == db_user_updated.id
        assert db_user_updated == db_event.is_managed_by
        assert db_reservation.user_booked == db_user_2
        assert db_reservation.for_event == db_event_2