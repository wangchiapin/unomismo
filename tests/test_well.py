# 井（unomismo）測試：進井計時、重新整理接著算、句子換檔、Y／N 鍵、離開歸零、?demo=、沒有雲端、localStorage 壞掉
import sys, time
from playwright.sync_api import sync_playwright
import common
from common import *

R = Runner()
KEY = 'well.enter'
def on(pg, id_): return pg.evaluate("id=>document.getElementById(id).classList.contains('active')", id_)
def ops(pg): return pg.evaluate("window.__ops||[]")

with sync_playwright() as p:
    # 1) 第一次來：開場 → 進入
    b, pg, errs = open_page(p)
    R.check(on(pg, 'intro'), '第一次來：先看到開場畫面')
    R.check(pg.evaluate("localStorage.getItem('%s')" % KEY) is None, '還沒進井：沒有存進入時間')
    pg.wait_for_function("document.getElementById('enterBtn').classList.contains('show')", timeout=15000)
    R.check(True, '開場打字完，「進入」鈕出現')
    pg.click('#enterBtn'); pg.wait_for_timeout(800)
    R.check(on(pg, 'hole'), '按進入：進到井裡')
    st = pg.evaluate("localStorage.getItem('%s')" % KEY)
    R.check(st is not None and abs(int(st) - time.time() * 1000) < 15000, '記下進入時間（現在）')
    R.check(pg.inner_text('#timer').startswith('你已經進入井裡 0天0小時0分'), '計時顯示：' + pg.inner_text('#timer'))
    o = [x for x in ops(pg) if x['k'] == 'set' and x['p'] == 'well_visitors/UID1']
    R.check(len(o) >= 1 and 'enteredAt' in o[0]['d'], '雲端報到：寫入 well_visitors/<uid>（只有時間，沒有名字）')
    R.check(set(o[0]['d'].keys()) <= {'enteredAt', 'lastSeen'}, '報到資料只有 enteredAt、lastSeen：' + str(list(o[0]['d'].keys())))
    # N：留下
    pg.keyboard.press('n'); pg.wait_for_timeout(200)
    R.check('那就再待一會兒吧' in pg.inner_text('#reply') and on(pg, 'hole'), '按 N：說「再待一會兒」，仍在井裡')
    R.check(pg.evaluate("localStorage.getItem('%s')" % KEY) == st, '按 N：入井時間不變')
    pg.click('#nBtn'); pg.wait_for_timeout(100)
    R.check(on(pg, 'hole'), '點 N 鈕：仍在井裡')
    # 重新整理接著算
    pg.reload(); pg.wait_for_timeout(1000)
    R.check(on(pg, 'hole') and not on(pg, 'intro'), '重新整理：直接回到井裡，不再看開場')
    R.check(pg.evaluate("localStorage.getItem('%s')" % KEY) == st, '重新整理：入井時間沒被洗掉')
    # Y：離開
    pg.keyboard.press('y'); pg.wait_for_timeout(500)
    R.check(on(pg, 'leave'), '按 Y：進入離開畫面')
    R.check(pg.evaluate("localStorage.getItem('%s')" % KEY) is None, '離開：清掉入井時間（歸零）')
    R.check(any(x['k'] == 'delete' and x['p'] == 'well_visitors/UID1' for x in ops(pg)), '離開：刪掉雲端那一筆')
    pg.wait_for_function("document.getElementById('againBtn').classList.contains('show')", timeout=20000)
    pg.reload(); pg.wait_for_timeout(1000)
    R.check(on(pg, 'intro'), '離開後重新整理：回到開場（不是接著算）')
    R.check(not errs, '沒有網頁錯誤 %s' % errs)
    b.close()

    # 2) 離開畫面「繼續回到井裡」會重新計時
    b, pg, errs = open_page(p, extra_init="localStorage.setItem('%s', String(Date.now()-3*3600*1000))" % KEY)
    R.check(on(pg, 'hole'), '已有入井時間：開頁直接在井裡')
    R.check(pg.inner_text('#timer').startswith('你已經進入井裡 0天3小時0分'), '接著算：已待 3 小時 → ' + pg.inner_text('#timer'))
    pg.click('#yBtn'); pg.wait_for_timeout(400)
    R.check(on(pg, 'leave'), '按 Y 鈕：進入離開畫面')
    pg.wait_for_function("document.getElementById('againBtn').classList.contains('show')", timeout=25000)
    R.check('你已經在井裡待了' in pg.inner_text('#leaveText') and '0天3小時0分' in pg.inner_text('#leaveText'), '離開畫面顯示待了多久：' + pg.inner_text('#leaveText').replace('\n', ' '))
    pg.click('#againBtn'); pg.wait_for_timeout(500)
    R.check(on(pg, 'hole') and pg.inner_text('#timer').startswith('你已經進入井裡 0天0小時0分'), '繼續回到井裡：重新從 0 算')
    b.close()

    # 3) 句子隨時間換檔（每 10 分鐘一句；滿一天後換成溫和的句子）
    for label, ms in (('0 分鐘', 0), ('25 分鐘', 25*60*1000), ('3 小時', 3*3600*1000), ('2 天', 2*86400*1000)):
        b, pg, errs = open_page(p, extra_init="localStorage.setItem('%s', String(Date.now()-%d))" % (KEY, ms))
        slot = ms // (10*60*1000)
        want = pg.evaluate("[%d >= 86400000 ? GENTLE[%d %% GENTLE.length] : SENTENCES[%d %% SENTENCES.length], LIGHT_LINE]" % (ms, slot, slot))
        got = pg.inner_text('#thought')
        R.check(got in want, f'已待 {label}：句子正確「{got}」')
        b.close()
    b, pg, errs = open_page(p, extra_init="localStorage.setItem('%s', String(Date.now()-86400000*2))" % KEY)
    R.check(pg.inner_text('#timer').startswith('你已經進入井裡 2天0小時0分'), '兩天格式：' + pg.inner_text('#timer'))
    b.close()

    # 4) localStorage 壞掉也能玩（用記憶體備援）
    b, pg, errs = open_page(p, extra_init="Object.defineProperty(window,'localStorage',{get(){throw new Error('blocked')}})")
    pg.wait_for_function("document.getElementById('enterBtn').classList.contains('show')", timeout=15000)
    pg.click('#enterBtn'); pg.wait_for_timeout(2500)
    R.check(on(pg, 'hole'), 'localStorage 不能用：仍可進井')
    pg.keyboard.press('y'); pg.wait_for_timeout(400)
    R.check(on(pg, 'leave'), 'localStorage 不能用：仍可離開')
    R.check(not errs, '沒有網頁錯誤 %s' % errs)
    b.close()

    # 5) Firebase 載不到：遊戲照常
    common.BLOCK_FB = True
    b, pg, errs = open_page(p, extra_init="localStorage.setItem('%s', String(Date.now()-60000))" % KEY)
    R.check(on(pg, 'hole'), '沒有雲端：照常進井')
    pg.click('#seeBtn'); pg.wait_for_timeout(1500)
    R.check('看不到井裡的人' in pg.inner_text('#othersCount'), '沒有雲端：看別人顯示「現在看不到井裡的人」：' + pg.inner_text('#othersCount'))
    pg.click('#backBtn'); pg.wait_for_timeout(200)
    pg.keyboard.press('y'); pg.wait_for_timeout(400)
    R.check(on(pg, 'leave'), '沒有雲端：照常離開')
    R.check(not errs, '沒有網頁錯誤 %s' % errs)
    b.close()
    common.BLOCK_FB = False

    # 6) ?demo=47：不連雲端、看別人
    b, pg, errs = open_page(p, '?demo=47', extra_init="localStorage.setItem('%s', String(Date.now()-60000))" % KEY)
    R.check(pg.is_visible('#seeBtn'), 'demo：「看看誰也在井裡」鈕出現')
    pg.click('#seeBtn'); pg.wait_for_timeout(1500)
    R.check('47' in pg.inner_text('#othersCount'), 'demo：總人數 47：' + pg.inner_text('#othersCount'))
    R.check(pg.locator('#tiles .tile').count() == 30, 'demo：顯示 30 個方塊（上限）：%d' % pg.locator('#tiles .tile').count())
    R.check(pg.locator('#tiles .tile.me').count() == 1, 'demo：有一個標示「我」')
    R.check('17' in pg.inner_text('#othersDeep'), 'demo：「還有 17 個人在更深的地方」：' + pg.inner_text('#othersDeep'))
    R.check(not any(x['k'] in ('set', 'delete') for x in ops(pg)), 'demo：沒有寫入／刪除雲端')
    pg.keyboard.press('y'); pg.wait_for_timeout(300)
    R.check(not on(pg, 'leave'), '看別人時按 Y 不會離開')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    R.check(pg.locator('#tiles .tile').count() == 0 and on(pg, 'hole'), 'Esc 關掉，方塊清空，回到井裡')
    pg.keyboard.press('y'); pg.wait_for_timeout(400)
    R.check(on(pg, 'leave'), '關掉後 Y 又能離開')
    R.check(not errs, '沒有網頁錯誤 %s' % errs)
    b.close()
    for n, want in ((1, '只有你'), (5, '5 個人')):
        b, pg, errs = open_page(p, f'?demo={n}', extra_init="localStorage.setItem('%s', String(Date.now()-60000))" % KEY)
        pg.click('#seeBtn'); pg.wait_for_timeout(1200)
        R.check(want in pg.inner_text('#othersCount') and pg.locator('#tiles .tile').count() == n, f'demo={n}：「{pg.inner_text("#othersCount")}」方塊 {pg.locator("#tiles .tile").count()}')
        b.close()

print('FAILS', R.fails); sys.exit(1 if R.fails else 0)
