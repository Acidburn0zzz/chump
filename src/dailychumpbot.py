#!/usr/bin/python    -*- coding: utf-8 -*-
# Copyright (c) 2001-2003 by
# Matt Biddulph and Edd Dumbill, Useful Information Company
# All rights reserved.
#
# License is granted to use or modify this software ("Daily Chump") for
# commercial or non-commercial use provided the copyright of the author is
# preserved in any distributed or derivative work.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESSED OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# $Id: dailychumpbot.py,v 1.16 2003/05/14 19:21:16 edmundd Exp $

# daily chump v 1.3

## irc interface to the chump engine

from dailychump import DailyChump,ChumpResponse,ChumpErrorResponse,ChumpInfoResponse
from ircbot import SingleServerIRCBot
from irclib import nm_to_n, irc_lower
import string
import time
import re

_version="1.3"

_M_QUIET=0
_M_PRIVMSG=1
_M_NOTICE=2

_A_GENERAL=0
_A_SPECIFIC=1

class DailyChumpBot(SingleServerIRCBot):
    def __init__(self, directory, channel, nickname,
                 server, port=6667, sheet=None, password=None,
                 mode=_M_NOTICE, addressing=_A_GENERAL,
                 use_unicode=0):
        SingleServerIRCBot.__init__(self, [(server, port)],
                                    nickname, nickname, password)
        self.nickname = nickname
        self.channel = channel
        self.foocount = 0
        self.chump = DailyChump(directory, use_unicode)
        self._mode=mode
        self._addressing=addressing
        self.use_utf8 = use_unicode
        if sheet!=None:
            self.chump.set_stylesheet(sheet)
        self.start()

    def tc(self, s):
        if self.use_utf8:
            try:
                return unicode(s, 'utf-8')
            except UnicodeError:
                return unicode(s, 'latin-1')
        else:
            return unicode(s, 'latin-1')

    def ec(self, s):
        if self.use_utf8:
            return s.encode('utf-8')
        else:
            try:
                return s.encode('latin-1')
            except UnicodeError:
                return "[unrepresentable in latin-1]"

    def on_topic(self,c,e):
        if e.arguments()[0] == self.channel:
            topic = self.tc(e.arguments()[1])
        else:
            topic = self.tc(e.arguments()[0])
        self.chump.set_topic(topic)

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_privmsg(self, c, e):
        nick = nm_to_n(e.source())
        msg = e.arguments()[0]
        output = self.process_input(c, nick, msg)
        if output != None:
            if isinstance(output, ChumpResponse):
                stroutput=output._str
            else:
                stroutput=output

        self.privmsg_multiline(c,nick,stroutput)

    def process_input(self, c, nick, msg, talking_to_me=1):
        """feeds instructions to the chump engine"""
        output = self.chump.process_input(nick, msg)
        # if not a content contribution, must be a bot command
        # but only if we're being addressed
        if output == None and talking_to_me:
            output = self.do_command(nick, msg)
        return output

    def on_pubmsg(self, c, e):
        msg = e.arguments()[0]
        nick = nm_to_n(e.source())

        parts = re.split(r"[,:]\s*", msg, 1)

        if (len(parts) > 1 and
            irc_lower(parts[0]) == irc_lower(self.connection.get_nickname())):
            talking_to_me=1
            msg=parts[1]
        else:
            talking_to_me=0

        if (self._addressing==_A_GENERAL or talking_to_me):
            output=self.process_input(c, nick, self.tc(msg), talking_to_me)

            # explanation of the following:
            # if in _M_NOTICE mode, do everything in public
            # if in _M_QUIET mode, suppress info messages
            # if in _M_PRIVMSG mode, send info & errors privately,
            #           but requested responses publicly
            if output != None:
                if isinstance(output, ChumpResponse):
                    stroutput=output._str
                else:
                    stroutput=output

                if (self._mode==_M_NOTICE or
                    (self._mode==_M_QUIET and
                     not isinstance(output, ChumpInfoResponse))):
                    self.notice_multiline(c, stroutput)
                elif self._mode==_M_PRIVMSG:
                    if (isinstance(output, ChumpInfoResponse) or
                        isinstance(output, ChumpErrorResponse)):
                        self.privmsg_multiline(c,nick,stroutput)
                    else:
                        self.notice_multiline(c,stroutput)

    def notice_multiline(self,c,msg):
        for x in string.split(msg,"\n"):
            c.notice(self.channel, self.ec(x))
            time.sleep(1)

    def privmsg_multiline(self,c,nick,msg):
        for x in string.split(msg,"\n"):
            c.privmsg(nick, self.ec(x))
            time.sleep(1)

    def do_command(self, nick, cmd):
        c = self.connection

        if cmd == "database":
            data = self.chump.get_database()
            return data
        elif cmd == "disconnect":
            self.disconnect()
        elif cmd == "help":
            return u"Post a URL by saying it on a line on its own\n"+u"To post an item without a URL, say BLURB:This is the title\n"+ u"I will reply with a label, for example A\n"+ u"You can then append comments by saying A:This is a comment\n"+ u"To title a link, use a pipe as the first character of the comment\n"+ u"Eg. A:|This is the title\n"+ u"To see the last 5 links posted, say "+self.nickname+":view\n"+ u"For more features, say "+self.nickname+":morehelp\n"
        elif cmd == "morehelp":
            return u"Put emphasis in a comment by using *asterisks*\n"+ u"To create an inline link in a comment, say:\n"+ u"A:Look at [this thing here|http://pants.heddley.com]\n"+ u"You can also link to inline images in a comment:\n"+ u"A:Chump logo +[alt-text|http://pants.heddley.com/chump.png]\n"+ u"To see the last n links, say "+self.nickname+":view n (where n is a number)\n"+ u"To see the details of a link labelled A, say A: on a line on its own\n"+ u"To view a particular comment, say An:, where n is the number of the comment\n" + u"To replace, say, the second comment on a link labelled A, say A2:replacement_text\n" + u"To delete the second comment on a link labelled A, say A2:\"\"\n" + u"To set keywords for a link labelled A, say A:->keyword1 keyword2 etc.\n" + u"Send any comments or questions to chump@heddley.com\n"
        elif cmd == "foo":
            c.action(self.channel,  self.ec(u"falls down a well."))
            self.foocount = self.foocount + 1
        elif cmd == "unfoo":
            if self.foocount > 0:
                c.action(self.channel, self.ec(u"clambers out of a well."))
                self.foocount = self.foocount - 1
            else:
                c.action(self.channel, self.ec(u"is not in a well, silly."))
        elif string.find(cmd,"view") == 0:
            viewmatch = re.compile("view\s+(\d+)")
            vm = viewmatch.match(cmd)
            if vm != None:
                count = string.atoi(vm.group(1))
                return self.chump.view_recent_items(count)
            else:
                return self.chump.view_recent_items()
        elif cmd == "die" or cmd == "depart" or cmd == "leave":
            self.die()
        elif cmd == "status":
            r=u"I am the Daily Chump Bot, version %s. "
            if self._mode==_M_NOTICE:
                r=r+u"In public mode. "
            elif self._mode==_M_PRIVMSG:
                r=r+u"In private mode. "
            elif self._mode==_M_QUIET:
                r=r+u"In quiet mode. "
            if self._addressing==_A_GENERAL:
                r=r+u"Promiscuous. "
            else:
                r=r+u"I must be addressed directly. "
            if self.use_utf8:
                r=r+u"I am in UTF-8 mode. "+unicode("日本語.", 'utf-8')+u" See?"
            else:
                r=r+u"I am in Latin-1 mode. "
            r=r+u"<http://usefulinc.com/chump/>"
            return r % _version
        else:
            return u"Not understood: " + cmd

        return None

def usage(invokedas):
    print """`%s' runs a weblog from an IRC channel.

Usage: %s [ -h | --help ]
       %s [ -v | --version ]
       %s OPTIONS

 -s, --server=STRING      IRC server to connect to. Required.
 -p, --port=INTEGER       IRC port number (defaults to 6667). Optional.
 -n, --nick=STRING        Nickname for the bot. Required.
 -c, --channel=STRING     IRC channel to join. Required. Quote # characters.
 -d, --dir=STRING         Directory for storing XML.
 -e, --stylesheet=STRING  Optional stylesheet URL to link from each XML file.
 -a, --password=STRING    Password to use to connect to IRC server.
 -i, --private            Send informative and error messages by private
                          message.
 -q, --quiet              Never send informative messages (can't be used
                          with -i).
 -r, --address            Only respond to public messages that address bot
                          by name.
 -u, --utf-8              Expect UTF-8, rather than Latin-1, input

Report bugs to <chump@heddley.com>""" % (invokedas, invokedas,
                                          invokedas, invokedas)

def version():
    print "Chump "+_version
    print
    print "Copyright (C) 2001, 2002 Matt Biddulph and Edd Dumbill"
    print """This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

Written by Matt Biddulph and Edd Dumbill. <http://usefulinc.com/chump/>"""

def main():
    import sys
    import getopt
    args = sys.argv[1:]
    optlist, args = getopt.getopt(args,'s:p:c:n:d:e:ha:vqiru',
                                  ["server=",
                                   "port=",
                                   "channel=",
                                   "nick=",
                                   "dir=",
                                   "stylesheet=",
                                   "help",
                                   "password=",
                                   "version",
                                   "quiet",
                                   "private",
                                   "address",
                                   "utf-8"])
    port = 6667

    directory = ''
    channel = ''
    nickname = ''
    server = ''
    password = ''
    sheet = None
    mode = _M_NOTICE
    addressing = _A_GENERAL
    use_unicode = 0

    for o in optlist:
        name = o[0]
        value = o[1]
        if name in ('-s', '--server'):
            server = value
        elif name in ('-p', '--port'):
            try:
                port = int(value)
            except ValueError:
                print "Error: Erroneous port."
                sys.exit(1)
        elif name in ('-c', '--channel'):
            channel = value
        elif name in ('-n', '--nick'):
            nickname = value
        elif name in ('-d', '--dir'):
            directory = value
        elif name in ('-e', '--stylesheet'):
            sheet = value
        elif name in ('-a', '--password'):
            password = value
        elif name in ('-i', '--private'):
            mode = _M_PRIVMSG
        elif name in ('-q', '--quiet'):
            mode = _M_QUIET
        elif name in ('-r', '--address'):
            addressing = _A_SPECIFIC
        elif name in ('-u', '--utf-8'):
            use_unicode = 1
        elif name in ('-h', '--help'):
            usage(sys.argv[0])
            sys.exit(0)
        elif name in ('-v', '--version'):
            version()
            sys.exit(0)

    if(directory != '' and channel != '' and
       nickname != '' and server != ''):
        bot = DailyChumpBot(directory, channel, nickname,
                            server, port, sheet, password,
                            mode, addressing, use_unicode)
        bot.start()
    else:
        usage(sys.argv[0])
        sys.exit(1)

if __name__ == "__main__":
    main()