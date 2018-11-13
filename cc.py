import cloudconvert
from cloudconvert import exceptions as ccex
import os


access_token_cc = os.environ['access_token_cc']


def to_gif(mp4file):
    api = cloudconvert.Api(access_token_cc)
    errmsg = ''
    fname = ''
    process = api.convert({
        "inputformat": "mp4",
        "outputformat": "gif",
        "input": "download",
        "file": mp4file,
        "converteroptions": {
            "command": '-i {INPUTFILE} -filter_complex "[0:v] split' 
                        '[a][b];[a] palettegen [p];[b][p] paletteuse" {OUTPUTFILE}'
        }
    })
    try:
        process.wait()
        process.download()
        fname = process.data['output']['filename']
    except ccex.BadRequest:
        errmsg = 'BadRequest'
    except ccex.ConversionFailed:
        errmsg = 'ConversionFailed'
    except ccex.HTTPError:
        errmsg = 'HTTPError'
    except ccex.InvalidParameterException:
        errmsg = 'InvalidParameterException'
    except ccex.InvalidResponse:
        errmsg = 'InvalidParameterException'
    except ccex.TemporaryUnavailable:
        errmsg = 'InvalidParameterException'
    except ccex.APIError:
        errmsg = 'APIError'

    process.delete()
    if errmsg != '':
        print('Error ({}) al convertir archivo ({}) a GIF'.format(errmsg, mp4file))
        return ''
    else:
        return fname
