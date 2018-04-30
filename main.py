import requests
import configparser
import time

settings = {}
streams_current = {}

def read_config(configfile):
    config = configparser.ConfigParser()
    config.read(configfile)

    # TODO: if we want to do more than access stream objects, baseurl should
    # be pointed at just api.twitch.tv and another variable added to control
    # which part of the API to go to (streams, channels, users, etc)
    info = {}
    info['check_every'] = float(config['client']['check_every'] or "10")
    info['baseurl'] = config['client']['baseurl']
    info['client-id'] = config['client']['client-id']
    info['usernames'] = [e.strip() for e in config['client']['usernames'].split(',')]
    info['slack_webhook'] = config['client']['slack_webhook']
    info['discord_webhook'] = config['client']['discord_webhook']
    return info

def main():
    global settings
    starttime = time.time()

    while True:
        settings = read_config('bot.ini')
        mainloop()
        delay = settings['check_every']
        time.sleep(delay - ((time.time() - starttime) % delay))

def mainloop():
    print("running main loop")
    global streams_current

    print("Current list of stream ids: {}".format(list(streams_current.keys())))

    # Get the current status of all users
    streams_new = get_streams()
    # Compare against the previous iteration of the loop
    # If this is the first time, streams_current will be empty so everything will be
    # new
    streamids_status = compare_streams(streams_current, streams_new)
    # Announce changes
    announce_streams(streamids_status, streams_current, streams_new)
    # copy new streams list to main list for next loop
    streams_current = streams_new
    
def get_streams():
    streams = {}
    headers = {'Client-ID': settings['client-id']}

    for user in settings['usernames']:
        print("Checking {}".format(user))
        # note: the API url is something like: api.twitch.tv/kraken/streams/hannibal127
        r = requests.get(settings['baseurl'] + user, headers=headers)
        res = r.json()

        print(res)

        if res['stream'] != None:
            stream_id = res['stream']['_id']
            streams[stream_id] = {}
            streams[stream_id]['username'] = user
            streams[stream_id]['game'] = res['stream']['game']
            streams[stream_id]['url']  = res['stream']['channel']['url']
            streams[stream_id]['status'] = res['stream']['channel']['status']
            streams[stream_id]['preview_l'] = res['stream']['preview']['large']
            
    return streams

def compare_streams(streams_current, streams_new):
    streamids_changed = {}
    streamids_changed['offline'] = []
    streamids_changed['online'] = []

    print("Current streams: {}".format(list(streams_current.keys())))
    print("New streams:     {}".format(list(streams_new.keys())))

    for key in streams_current:
        if key not in streams_new:
            streamids_changed['offline'].append(key)

    for key in streams_new:
        if key not in streams_current:
            streamids_changed['online'].append(key)
    
    print("Streams that just went offline: {}".format(streamids_changed['offline']))
    print("Streams that just went online:  {}".format(streamids_changed['online']))

    return streamids_changed

def announce_streams(streamids_changed, streams_current, streams_new):
    for streamid in streamids_changed['online']:
        ann_text = "{} has gone live on Twitch!".format(streams_new[streamid]['username'])
        att_text = "{}\nStatus: {}\nGame: {}".format(
                streams_new[streamid]['url'],
                streams_new[streamid]['status'],
                streams_new[streamid]['game'])

        payload = {
                'text': ann_text,
                'attachments': [
                    {
                        'color': '#00FF00',
                        'text': att_text,
                        'image_url': streams_new[streamid]['preview_l']
                    }
                ]
        }

        p = requests.post(settings['slack_webhook'], json=payload)
        q = requests.post(settings['discord_webhook'], json=payload)

    for streamid in streamids_changed['offline']:
        ann_text = "{} stopped streaming on Twitch.".format(streams_current[streamid]['username'])
        att_text = "{}\nStatus: {}\nGame: {}".format(
                streams_current[streamid]['url'],
                streams_current[streamid]['status'],
                streams_current[streamid]['game'])

        payload = {
                'text': ann_text,
                'attachments': [
                    {
                        'color': '#FF0000',
                        'text': att_text
                    }
                ]
        }
        p = requests.post(settings['slack_webhook'], json=payload)
        q = requests.post(settings['discord_webhook'], json=payload)

if __name__ == "__main__":
    main()
