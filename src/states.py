import enum


class OlimpCodes(enum.Enum):
    ok = 'OK'
    error_response = 'ERROR_RESPONSE'
    error_games_pars = 'ERROR_GAMES_PARS'
    error_get_coeffs = 'ERROR_GET_COEFFICIENTS'
    error_get_list = 'ERROR_GET_LIST_FOR_COMPARE'
