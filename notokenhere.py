import bot
import os
import time
from datetime import datetime
from discord.ext import commands
intents=bot.Intents.default()
intents.message_content = True
client = bot.Client(intents=intents)


##########################   constant   ##########################


currentTime = datetime.now()
year=['元年']
fbnc=[0,1,1,2,3,5,8,13,21,34,55,89,144,233,377,610,987]
timer={}
##########################   some function   ##########################


def cut_string(s):
    temp=''
    for i in range( len(s) ):
        if(s[i] != '#'):
            temp=temp+s[i]
        else:
            break
    return temp

def find(who):
    with open('namelist.txt', 'r') as f:
        for i in f:
            if(i==who+'\n'):
                return 1
    return 0

def next_day(date):
    date=date.split('/')
    date[0]='S'
    month=int(date[2])
    day=int(date[3])
    if(day==fbnc[month]):
        month+=1
        day=1
    else:
        day+=1
    temp=''
    date[2]=str(month)
    date[3]=str(day)
    temp=date[0]+'/'+date[1]+'/'+date[2]+'/'+date[3]
    return temp        
    
def sec_to_hms(num):
    return str(num//3600)+':'+str((num%3600)//60)+':'+str((num%60))

def await_output(temp):
    with open(temp,'r') as g:
        f=g.readlines()
        date=f[-1]
        date=date.split('/')
        return '你的'+date[1]+date[2]+'月'+date[3]+'日'

def check(who, what):
    temp='name/'+who+'.txt'
    if os.path.exists(temp):
        pass
    elif (what=='sign_up'):
        return ['sign_up',who]
    with open(temp, 'r') as g:
        f=g.readlines()
        if(f[-1][0]=='S' and what=='oyasumi'):
            return ['finish',who]
        if(f[-1][0]=='S' and what=='ohiyo'):
            return ['error','double_ohiyo']
        if(f[-1][0]=='E' and what=='ohiyo'):
            return ['start',who]
        if(f[-1][0]=='E' and what=='oyasumi'):
            return ['error','double_oyasumi']
    return ['error','invalid_command']

def what_to_do(command):#command[0]==command type, command[1]==who
    temp='name/'+command[1]+'.txt'
    if(command[0]=='error'):
        #error message
        error_message={
            'double_ohiyo':'你不是起床了嗎',
            'double_oyasumi':'沒想到你是那種說晚安之後去滑手機的人',
            'invalid_command':'void command'
            }
        return error_message[command[1]]
    if(command[0]=='sign_up'):
        with open(temp,'w') as f:
            f.write('S/'+year[-1]+'/1/1/\n')
            timer[command[1]]=round(time.time())
        return '今天是'+await_output(temp)
    if(command[0]=='finish'):
        s=''
        with open(temp,'r') as g:
            f=g.readlines()
            s='E'+f[-1][1:-1]+'/'
        with open(temp,'a') as f:
            f.write(s)
            during_time=( round(time.time()) - timer[command[1]])
            f.write(' '+sec_to_hms(during_time)+'\n')
        del timer[command[1]]
        return await_output(temp)+'結束了,歷時'+sec_to_hms(during_time)
    if(command[0]=='start'):
        s=''
        with open(temp,'r') as g:
            f=g.readlines()
            s=next_day(f[-1])+'/\n'
        with open(temp,'a') as f:
            f.write(s)
        timer[command[1]]=round(time.time())
        return '今天是'+await_output(temp)


##########################   discord bot command   ##########################

@client.event
async def on_ready():
    print(client.user," login")

@client.event
async def on_message(message):
    who=cut_string(str(message.author))
    if(message.author == client.user):
        return
    
    if(message.content == '/help'):
        hint='/help:查看ssh說明書\n/sign_up:如果你之前都沒用過ssh指令(/help不算),用這個開始你的第一天\n/ohiyo:當你開始新的一天的時候打這個\n/oyasumi:當你準備邁向明天的時候打這個'
        await message.channel.send(hint)
    
    if(message.content == '/sign_up'):
        if find(who):
            await message.channel.send( what_to_do(check(who,'sign_up')) ) 
        else:
            await message.channel.send("who r u?")
    
    if(message.content == '/ohiyo'):
        if find(who):
            await message.channel.send( what_to_do(check(who,'ohiyo')) )
        else:
            await message.channel.send("who r u?")
    
    if(message.content == '/oyasumi'):
        if find(who):
            await message.channel.send( what_to_do(check(who,'oyasumi')) )
        else:
            await message.channel.send("who r u?")
    
    if(message.content == '/to_fix'):
        stack=[]
        for i in timer:
            stack.append(i)
        for i in stack:
            what_to_do(check(i,'oyasumi'))
        await message.channel.send('yee')
    
    if(message.content =='/print_timer'):
        print(timer)
        await message.channel.send('yee')


##########################   else   ##########################
    

client.run("token")
