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
            "command": '-i {INPUTFILE} -filter_complex '
                       '"scale=w=\'min(240,iw)\':h=-1,split [a][b];'
                       '[a] palettegen=stats_mode=\'diff\' [p];'
                       '[b] fifo [c];'
                       '[c] [p] paletteuse=diff_mode=\'rectangle\'"'
                       ' {OUTPUTFILE}'
            # https://engineering.giphy.com/how-to-make-gifs-with-ffmpeg/
            # https://ffmpeg.org/ffmpeg-filters.html
        }
    })
    try:
        process.wait()
        process.download()
        fname = process.data['output']['filename']
    except ccex.BadRequest as e:
        errmsg = 'BadRequest ' + e.args[0]
    except ccex.ConversionFailed as e:
        errmsg = 'ConversionFailed ' + e.args[0]
    except ccex.HTTPError as e:
        errmsg = 'HTTPError ' + e.args[0]
    except ccex.InvalidParameterException as e:
        errmsg = 'InvalidParameterException ' + e.args[0]
    except ccex.InvalidResponse as e:
        errmsg = 'InvalidParameterException ' + e.args[0]
    except ccex.TemporaryUnavailable as e:
        errmsg = 'InvalidParameterException ' + e.args[0]
    except ccex.APIError as e:
        errmsg = 'APIError ' + e.args[0]

    process.delete()
    if errmsg != '':
        print('Error ({}) al convertir archivo ({}) a GIF'.format(errmsg, mp4file))
        return mp4file
    else:
        return fname
