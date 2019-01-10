import logging

from homekit.model import Categories


def parse_manufacturer_specific(input_data):
    logging.debug('manufacturer specific data: %s', input_data.hex())

    # the type must be 0x06 as defined on page 124 table 6-29
    ty = input_data[0]
    input_data = input_data[1:]
    if ty == 0x06:
        ty = 'HomeKit'

        ail = input_data[0]
        logging.debug('advertising interval %s', '{0:02x}'.format(ail))
        length = ail & 0b00011111
        if length != 13:
            logging.debug('error with length of manufacturer data')
        input_data = input_data[1:]

        sf = input_data[0]
        if sf == 0:
            sf = 'paired'
        elif sf == 1:
            sf = 'unpaired'
        else:
            sf = 'error'
        input_data = input_data[1:]

        device_id = (':'.join(input_data[:6].hex()[0 + i:2 + i] for i in range(0, 12, 2))).upper()
        input_data = input_data[6:]

        acid = int.from_bytes(input_data[:2], byteorder='little')
        input_data = input_data[2:]

        gsn = int.from_bytes(input_data[:2], byteorder='little')
        input_data = input_data[2:]

        cn = input_data[0]
        input_data = input_data[1:]

        cv = input_data[0]
        input_data = input_data[1:]
        if len(input_data) > 0:
            logging.debug('remaining data: %s', input_data.hex())
        return {'manufacturer': 'apple', 'type': ty, 'sf': sf, 'deviceId': device_id, 'acid': acid,
                'gsn': gsn, 'cn': cn, 'cv': cv, 'category': Categories[int(acid)]}

    return {'manufacturer': 'apple', 'type': ty}
