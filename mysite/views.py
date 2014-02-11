# -*- coding: utf-8 -*-
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.encoding import smart_str, smart_unicode

import xml.etree.ElementTree as ET
import urllib2,time,hashlib
import json

TOKEN = "alanleeworld"

YOUDAO_KEY = 1693811358
YOUDAO_KEY_FROM = "alanleeworld"
YOUDAO_DOC_TYPE = "xml"

@csrf_exempt
def handleRequest(request):
        if request.method == 'GET':
                #response = HttpResponse(request.GET['echostr'],content_type="text/plain")
                response = HttpResponse(checkSignature(request),content_type="text/plain")
                return response
        elif request.method == 'POST':
                #c = RequestContext(request,{'result':responseMsg(request)})
                #t = Template('{{result}}')
                #response = HttpResponse(t.render(c),content_type="application/xml")
                response = HttpResponse(responseMsg(request),content_type="application/xml")
                return response
        else:
                return None

def checkSignature(request):
        global TOKEN
        signature = request.GET.get("signature", None)
        timestamp = request.GET.get("timestamp", None)
        nonce = request.GET.get("nonce", None)
        echoStr = request.GET.get("echostr",None)

        token = TOKEN
        tmpList = [token,timestamp,nonce]
        tmpList.sort()
        tmpstr = "%s%s%s" % tuple(tmpList)
        tmpstr = hashlib.sha1(tmpstr).hexdigest()
        if tmpstr == signature:
                return echoStr
        else:
                return None
            
def responseMsg(request):
        return responseMsgDouban(request);
    
def responseMsgDouban(request):
        rawStr = smart_str(request.raw_post_data)
        msg = paraseMsgXml(ET.fromstring(rawStr))

      
        if msg["MsgType"] == "event":
            textTpl = """<xml>
             <ToUserName><![CDATA[%s]]></ToUserName>
             <FromUserName><![CDATA[%s]]></FromUserName>
             <CreateTime>%s</CreateTime>
             <MsgType><![CDATA[text]]></MsgType>
             <Content><![CDATA[%s]]></Content>
             <FuncFlag>0</FuncFlag>
             </xml>"""
            echostr = textTpl % (msg['FromUserName'], msg['ToUserName'], str(int(time.time())),u"欢迎关注，输入电影名称即可快速查询电影讯息！")
            return echostr
    
        queryStr = msg.get('Content','You have input nothing~')
        
        #search movie id 
        movieurlbase = "http://api.douban.com/v2/movie/search"
        DOUBAN_APIKEY = "0e6c09e84c33c6bd2b441db8e49b5437"  # your DouBan APIKEY
        url = '%s?q=%s&apikey=%s' % (movieurlbase, urllib2.quote(queryStr), DOUBAN_APIKEY)
        resp = urllib2.urlopen(url)
        movieid = json.loads(resp.read())
        
        #search movie info
        movieurlbase1 = "http://api.douban.com/v2/movie/subject/"
        info_url = '%s%s?apikey=%s' % (movieurlbase1, movieid["subjects"][0]["id"], DOUBAN_APIKEY)
        info_resp = urllib2.urlopen(info_url)
        description = json.loads(info_resp.read())
        description = ''.join(description['summary'])
        pictextTpl = "<xml><ToUserName><![CDATA[%s]]></ToUserName><FromUserName><![CDATA[%s]]></FromUserName><CreateTime>%s</CreateTime><MsgType><![CDATA[news]]></MsgType><ArticleCount>1</ArticleCount><Articles><item><Title><![CDATA[%s]]></Title><Description><![CDATA[%s]]></Description><PicUrl><![CDATA[%s]]></PicUrl><Url><![CDATA[%s]]></Url></item></Articles><FuncFlag>1</FuncFlag></xml> "
        echostr = pictextTpl % (msg['FromUserName'], msg['ToUserName'], str(int(time.time())),movieid["subjects"][0]["title"], description,movieid["subjects"][0]["images"]["large"], movieid["subjects"][0]["alt"])
        return echostr

def responseMsgYoudao(request):
        rawStr = smart_str(request.raw_post_data)
        #rawStr = smart_str(request.POST['XML'])
        msg = paraseMsgXml(ET.fromstring(rawStr))
        
        queryStr = msg.get('Content','You have input nothing~')

        raw_youdaoURL = "http://fanyi.youdao.com/openapi.do?keyfrom=%s&key=%s&type=data&doctype=%s&version=1.1&q=" % (YOUDAO_KEY_FROM,YOUDAO_KEY,YOUDAO_DOC_TYPE)        
        youdaoURL = "%s%s" % (raw_youdaoURL,urllib2.quote(queryStr))

        req = urllib2.Request(url=youdaoURL)
        result = urllib2.urlopen(req).read()

        replyContent = paraseYouDaoXml(ET.fromstring(result))

        return getReplyXml(msg,replyContent)

def paraseMsgXml(rootElem):
        msg = {}
        if rootElem.tag == 'xml':
                for child in rootElem:
                        msg[child.tag] = smart_str(child.text)
        return msg

def paraseYouDaoXml(rootElem):
        replyContent = ''
        if rootElem.tag == 'youdao-fanyi':
                for child in rootElem:
                        # 错误码
                        if child.tag == 'errorCode':
                                if child.text == '20':
                                        return 'too long to translate\n'
                                elif child.text == '30':
                                        return 'can not be able to translate with effect\n'
                                elif child.text == '40':
                                        return 'can not be able to support this language\n'
                                elif child.text == '50':
                                        return 'invalid key\n'

                        # 查询字符串
                        elif child.tag == 'query':
                                replyContent = "%s%s\n" % (replyContent, child.text)

                        # 有道翻译
                        elif child.tag == 'translation': 
                                replyContent = '%s%s\n%s\n' % (replyContent, '-' * 3 + u'有道翻译' + '-' * 3, child[0].text)

                        # 有道词典-基本词典
                        elif child.tag == 'basic': 
                                replyContent = "%s%s\n" % (replyContent, '-' * 3 + u'基本词典' + '-' * 3)
                                for c in child:
                                        if c.tag == 'phonetic':
                                                replyContent = '%s%s\n' % (replyContent, c.text)
                                        elif c.tag == 'explains':
                                                for ex in c.findall('ex'):
                                                        replyContent = '%s%s\n' % (replyContent, ex.text)

                        # 有道词典-网络释义
                        elif child.tag == 'web': 
                                replyContent = "%s%s\n" % (replyContent, '-' * 3 + u'网络释义' + '-' * 3)
                                for explain in child.findall('explain'):
                                        for key in explain.findall('key'):
                                                replyContent = '%s%s\n' % (replyContent, key.text)
                                        for value in explain.findall('value'):
                                                for ex in value.findall('ex'):
                                                        replyContent = '%s%s\n' % (replyContent, ex.text)
                                        replyContent = '%s%s\n' % (replyContent,'--')
        return replyContent

def getReplyXml(msg,replyContent):
        extTpl = "<xml><ToUserName><![CDATA[%s]]></ToUserName><FromUserName><![CDATA[%s]]></FromUserName><CreateTime>%s</CreateTime><MsgType><![CDATA[%s]]></MsgType><Content><![CDATA[%s]]></Content><FuncFlag>0</FuncFlag></xml>";
        extTpl = extTpl % (msg['FromUserName'],msg['ToUserName'],str(int(time.time())),'text',replyContent)
        return extTpl