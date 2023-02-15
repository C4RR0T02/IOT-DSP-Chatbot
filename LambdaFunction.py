"""
This sample demonstrates an implementation of the Lex Code Hook Interface
in order to serve a sample bot which manages reservations for hotel rooms and car rentals.
Bot, Intent, and Slot models which are compatible with this sample can be found in the Lex Console
as part of the 'BookTrip' template.

For instructions on how to set up and test this bot, as well as additional samples,
visit the Lex Getting Started documentation http://docs.aws.amazon.com/lex/latest/dg/getting-started.html.
"""

import json
import datetime
import time
import os
import dateutil.parser
import logging

room_types = ['cecil hotel', 'old changi hospital', 'doll island', 'gonjiam asylum']


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


# --- Helpers that build all of the responses ---


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def confirm_intent(session_attributes, intent_name, slots, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ConfirmIntent',
            'intentName': intent_name,
            'slots': slots,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


# --- Helper Functions ---


def safe_int(n):
    """
    Safely convert n value to int.
    """
    if n is not None:
        return int(n)
    return n


def try_ex(func):
    """
    Call passed in function in try block. If KeyError is encountered return None.
    This function is intended to be used to safely access dictionary.

    Note that this function would have negative impact on performance.
    """

    try:
        return func()
    except KeyError:
        return None



def generate_booking_price(nights, room_type):
    """
    Generates booking price
    """
    room_types = ['cecil hotel', 'old changi hospital', 'doll island', 'gonjiam asylum']
    location_prices = [150,50,200,180]
    price = nights * location_prices[room_types.index(room_type.lower())]

    return price

# Checking Function to throw errors
def isvalid_contactnumber(contact_number):
    if len(contact_number) == 8:
        return contact_number
    else:
        return False


def isvalid_room_type(room_type, room_types):
    if room_type.lower() in room_types:
        return True
    else:
        return False


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False

'''
def get_day_difference(later_date, earlier_date):
    later_datetime = dateutil.parser.parse(later_date).date()
    earlier_datetime = dateutil.parser.parse(earlier_date).date()
    return abs(later_datetime - earlier_datetime).days


def add_days(date, number_of_days):
    new_date = dateutil.parser.parse(date).date()
    new_date += datetime.timedelta(days=number_of_days)
    return new_date.strftime('%Y-%m-%d')
'''

# Validation code
def build_validation_result(isvalid, violated_slot, message_content):
    return {
        'isValid': isvalid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def validate_tour(slots):
    contact_name = try_ex(lambda: slots['ContactName'])
    contact_number = safe_int(try_ex(lambda: slots['ContactNumber']))
    room_type = try_ex(lambda: slots['BookingLocation'])
    checkin_date = try_ex(lambda: slots['CheckInDate'])
    nights = safe_int(try_ex(lambda: slots['Nights']))
    
    # Check Contact Number
    if contact_number and not isvalid_contactnumber(contact_number):
        return build_validation_result(
            False,
            'ContactNumber',
            'Kindly enter a valid contact number'
        )
    # Check Location Booking
    if room_type and not isvalid_room_type(room_type):
        return build_validation_result(
            False,
            'BookingLocation',
            'We currently do not support {} as a destination.  Kindly enter a supported site?'.format(room_type)
        )
    # Check Date
    if checkin_date:
        if not isvalid_date(checkin_date):
            return build_validation_result(False, 'CheckInDate', 'I did not understand your check in date.  When would you like to check in?')
        if datetime.datetime.strptime(checkin_date, '%Y-%m-%d').date() <= datetime.date.today():
            return build_validation_result(False, 'CheckInDate', 'Reservations must be scheduled at least one day in advance.  Can you try a different date?')
    # Check Time of Visit
    if nights is not None and (nights < 1 or nights > 30):
        return build_validation_result(
            False,
            'Nights',
            'You can make a reservations for from one to thirty nights.  How many nights would you like to stay for?'
        )

    
    return {'isValid': True}


""" --- Functions that control the bot's behavior --- """


def book_hotel(intent_request):
    """
    Performs dialog management and fulfillment for booking a hotel.

    Beyond fulfillment, the implementation for this intent demonstrates the following:
    1) Use of elicitSlot in slot validation and re-prompting
    2) Use of sessionAttributes to pass information that can be used to guide conversation
    """

    contact_name = try_ex(lambda: intent_request['currentIntent']['slots']['ContactName'])
    contact_number = safe_int(try_ex(lambda: intent_request['currentIntent']['slots']['ContactNumber']))
    room_type = try_ex(lambda: intent_request['currentIntent']['slots']['BookingLocation'])
    checkin_date = try_ex(lambda: intent_request['currentIntent']['slots']['CheckInDate'])
    nights = safe_int(try_ex(lambda: intent_request['currentIntent']['slots']['Nights']))
    

    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    # Load confirmation history and track the current reservation.
    reservation = json.dumps({
        'ReservationType': 'TourBooking',
        'ReservationName': contact_name,
        'ReservationContact': contact_number,
        'Location': room_type,
        'CheckInDate': checkin_date,
        'Nights': nights
    })

    session_attributes['currentReservation'] = reservation

    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Validate any slots which have been specified.  If any are invalid, re-elicit for their value
        validation_result = validate_tour(intent_request['currentIntent']['slots'])
        if not validation_result['isValid']:
            slots = intent_request['currentIntent']['slots']
            slots[validation_result['violatedSlot']] = None

            return elicit_slot(
                session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )

        # Otherwise, let native DM rules determine how to elicit for slots and prompt for confirmation.  Pass price
        # back in sessionAttributes once it can be calculated; otherwise clear any setting from sessionAttributes.
        if room_type and checkin_date and nights:
            price = generate_booking_price(nights, room_type)
            session_attributes['currentReservationPrice'] = price
        else:
            try_ex(lambda: session_attributes.pop('currentReservationPrice'))

        session_attributes['currentReservation'] = reservation
        return delegate(session_attributes, intent_request['currentIntent']['slots'])

    # Booking the trip.  In a real application, this would likely involve a call to a backend service.
    logger.debug('bookTrip under={}'.format(reservation))

    '''
    try_ex(lambda: session_attributes.pop('currentReservationPrice'))
    try_ex(lambda: session_attributes.pop('currentReservation'))
    session_attributes['lastConfirmedReservation'] = reservation
    '''

    # Return Message to Users
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'Thanks, I have placed your reservation under {} with the number {}. '
            'You will be contacted before the tour date for confirmation. '
            'Please let me know if you would like to book another tour.'.format(contact_name, contact_number)
        }
    )



# --- Intents ---


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'BookHotel':
        return book_hotel(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


# --- Main handler ---


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(repr(event)))

    return dispatch(event)
