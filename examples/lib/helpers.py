from itertools import islice

# Helper functions
def clean_up_name(name):
    return name.replace('/', '_').replace(' ', '_').lower()

def chunks(data, size):
    it = iter(data)
    for i in range(0, len(data), size):
        yield {k:data[k] for k in islice(it, size)}

def map_months_to_date(year, values=None):
    month_map = { 
        'JANUARY': { 'start_time': f'{year}-01-01', 'end_time': f'{year}-01-31' }, 
        'FEBRUARY': { 'start_time': f'{year}-02-01', 'end_time': f'{year}-02-{29 if (year % 4) == 0 else 28}' }, 
        'MARCH': { 'start_time': f'{year}-03-01', 'end_time': f'{year}-03-31' }, 
        'APRIL': { 'start_time': f'{year}-04-01', 'end_time': f'{year}-04-30' }, 
        'MAY': { 'start_time': f'{year}-05-01', 'end_time': f'{year}-05-31' }, 
        'JUNE': { 'start_time': f'{year}-06-01', 'end_time': f'{year}-06-30' }, 
        'JULY': { 'start_time': f'{year}-07-01', 'end_time': f'{year}-07-31' }, 
        'AUGUST': { 'start_time': f'{year}-08-01', 'end_time': f'{year}-08-31' }, 
        'SEPTEMBER': { 'start_time': f'{year}-09-01', 'end_time': f'{year}-09-30' }, 
        'OCTOBER': { 'start_time': f'{year}-10-01', 'end_time': f'{year}-10-31' }, 
        'NOVEMBER': { 'start_time': f'{year}-11-01', 'end_time': f'{year}-11-30' }, 
        'DECEMBER': { 'start_time': f'{year}-12-01', 'end_time': f'{year}-12-31'}
        }

    results = []
    
        
    if values:
        # Check if all the values are zero, if so then do not add them to the payload
        if all(value == 0 for value in values.values()):
            return []
    
        # add in the values to the dictionary if they match the key
        # Values can be in the form of the following:
            # "ELECTRICITYUSE_KBTU_JANUARY": 3017508.8,
            # "ELECTRICITYUSE_KBTU_FEBRUARY": 2722907.3,
            # "ELECTRICITYUSE_KBTU_MARCH": 2728590.7,

        for key, value in values.items():
            for month in month_map:
                if month in key:
                    month_map[month]['reading'] = value
                    month_map[month]['source_unit'] = 'kBtu (Thousand BTU)'
                    month_map[month]['conversion_factor'] = 1
                    results.append(month_map[month])
    else:
        for key, value in month_map.items():
            results.append(value)

    return results
