"""คำศัพท์พื้นฐานที่ใช้ช่วยตัดสินว่าข้อความ "ดูเหมือน" ภาษาไหน

เพิ่มคำเองได้ในไฟล์ words_en.txt / words_th.txt (หนึ่งคำต่อบรรทัด) ในโฟลเดอร์เดียวกัน
"""
import os

EN_WORDS_TEXT = """
a about above across act action add after again against age ago agree air all allow almost alone along already also
although always am among an and animal another answer any anyone anything app apple are area arm around art as ask at
away baby back bad bag ball bank base be beautiful because become bed been before begin behind being believe best better
between big bill bit black blue board body book both box boy break bring brother build business but buy by call came
can car card care case cat cause center certain chair change check child children city class clear close code cold
color come common company computer control cool cost could country course cover create cut dad data day dead deal dear
death decide deep design did die different dinner do doctor does dog doing done door down draw dream drink drive drop
during each early east easy eat edit else email end enough even evening event ever every everyone everything example
eye face fact fall family far fast father feel few field file find fine finish fire first fish five floor fly follow
food foot for form found four free friend from front full fun game gave get girl give glad go god going good got great
green group grow guy had hair half hand happen happy hard has have he head hear heart hello help her here hey hi high
him his hit hold home hope hot hour house how however huge human hundred i idea if image important in info inside into
is issue it its job join just keep key kid kill kind king know land language large last late later laugh law learn
least leave left less let letter level life light like line list listen little live long look lose lot love low made
main make man many market may maybe me mean meet meeting member message might mind minute miss model mom money month
more morning most mother move movie much music must my name near need never new news next nice night no none nor not
note nothing now number of off office often oh ok okay old on once one only open or order other our out over own page
paper parent part party pass past pay people per person phone pick picture place plan play please point power present
price problem program project put question quick quite rain rather read ready real really reason red remember report
rest right road room run said same save saw say school screen sea second see seem self send sense set seven several
she short should show side simple since sing sir sister sit six size sleep small so some someone something sometimes
son song soon sorry sound speak special stand start state stay still stop story street strong student study such sun
sure system table take talk tea teach team tell ten test text than thank thanks that the their them then there these
they thing think this those though thought three through time to today together told tomorrow too took top total town
travel tree true try turn two type under understand until up update upon us use used user very video view visit wait
walk wall want war was watch water way we week well went were what when where whether which while white who whole why
wife will win window with within without woman word work world would write wrong yeah year yes yesterday yet you young
your yourself zero lol omg btw thx pls plz wow cool nice hmm hello hi bye goodbye night morning afternoon login
password admin server client api git push pull commit branch merge python java script html css json http www com net
org google facebook youtube line windows microsoft apple iphone android mac pc chrome excel word powerpoint office
zoom teams meet chat call link share download upload install update file folder save delete copy paste print cancel
""".split()

TH_WORDS_TEXT = """
ที่ และ ใน การ เป็น ของ มี ได้ ไม่ ให้ จะ ว่า กับ แต่ ก็ มา ไป นี้ คน อยู่ แล้ว ด้วย ความ จาก เขา เรา ผม ฉัน คุณ ทำ
ไว้ หรือ เพื่อ โดย ถึง ยัง เมื่อ อย่าง ซึ่ง นั้น กัน ต้อง ตาม อีก ทาง ขึ้น ออก ใช้ เลย มาก วัน เวลา ปี เดือน ดี ใหม่
สวัสดี ครับ ค่ะ คะ นะ จ้ะ จ้า ขอบคุณ ขอโทษ ไหม มั้ย อะไร ทำไม ที่ไหน เท่าไหร่ อย่างไร ยังไง ใคร เมื่อไหร่ ตอนนี้ วันนี้
พรุ่งนี้ เมื่อวาน กิน ข้าว น้ำ นอน ไป มา ดู ฟัง พูด อ่าน เขียน เรียน ทำงาน งาน บ้าน รถ เงิน ซื้อ ขาย ร้าน ตลาด โรงเรียน
โรงพยาบาล บริษัท ประเทศ ไทย ภาษา อังกฤษ คอมพิวเตอร์ โทรศัพท์ มือถือ ข้อความ ส่ง รับ ถาม ตอบ รู้ เข้าใจ คิด ชอบ รัก
อยาก ต้องการ เห็น บอก เรื่อง สิ่ง ตัว หนึ่ง สอง สาม สี่ ห้า หก เจ็ด แปด เก้า สิบ ร้อย พัน หมื่น แสน ล้าน พ่อ แม่ ลูก
พี่ น้อง เพื่อน แฟน ครู นักเรียน หมอ คนไทย ใหญ่ เล็ก ยาว สั้น ร้อน หนาว เย็น สวย น่ารัก เก่ง ง่าย ยาก เร็ว ช้า ใกล้ ไกล
ก่อน หลัง ข้าง บน ล่าง หน้า เข้า กลับ ถ้า เพราะ จึง แค่ เท่านั้น ทุก บาง หลาย ทั้ง เอง จริง ๆ เหมือน กว่า ที่สุด ประมาณ
ช่วย ลอง เริ่ม จบ เสร็จ แก้ ไข ปัญหา ระบบ ข้อมูล โปรแกรม ไฟล์ เปิด ปิด ลบ บันทึก พิมพ์ ค้นหา หา เจอ ตรวจ สอบ ทดสอบ
ประชุม โครงการ ลูกค้า ราคา บาท สินค้า บริการ สั่ง จ่าย โอน บัญชี ธนาคาร อาหาร อร่อย หิว อิ่ม เที่ยว ทะเล ภูเขา
เมือง กรุงเทพ จังหวัด ถนน ทำอะไร อยู่ไหน ได้ไหม ไม่ได้ ไม่มี ไม่ใช่ ใช่ ครับผม โอเค ได้เลย แน่นอน คงจะ อาจจะ น่าจะ
คือ เคย กำลัง พึ่ง เพิ่ง ยิ่ง ค่อย ช่วง ตอน ครั้ง เช้า สาย บ่าย เย็น ค่ำ คืน กลางคืน วันจันทร์ อังคาร พุธ พฤหัส ศุกร์ เสาร์
อาทิตย์ สัปดาห์ ชั่วโมง นาที วินาที เกม หนัง เพลง ร้องเพลง เล่น กีฬา ฟุตบอล สุขภาพ ป่วย ไข้ ยา ใจ สบาย สบายดี
เหนื่อย ง่วง สนุก เศร้า โกรธ กลัว ดีใจ เสียใจ หัวเราะ ร้องไห้ ยิ้ม ขำ ตลก ฝน ฟ้า แดด ลม อากาศ ต้นไม้ ดอกไม้ หมา แมว
นก ปลา ไก่ หมู วัว ผัก ผลไม้ กาแฟ ชา นม ขนม แบบ ชนิด เรียบร้อย พร้อม ส่วน รวม แยก เพิ่ม ลด มากกว่า น้อย ราว ครบ
ตั้ง ตั้งแต่ จนถึง ระหว่าง ภายใน ภายนอก เกี่ยวกับ สำหรับ แทน เลือก ตัดสินใจ ยืนยัน ยกเลิก ติดต่อ โทร อีเมล เว็บ
แอป ออนไลน์ อินเทอร์เน็ต ไลน์ เฟซบุ๊ก ภาพ รูป วิดีโอ เสียง สี แดง เขียว น้ำเงิน เหลือง ขาว ดำ ชมพู ม่วง ส้ม
""".split()


def _load_extra(name):
    """อ่านคำเพิ่มเติมจากโฟลเดอร์โค้ด และ %APPDATA%\\PimPid (สำหรับตัวที่ติดตั้งแล้ว)"""
    dirs = [os.path.dirname(os.path.abspath(__file__)),
            os.path.join(os.environ.get("APPDATA", ""), "PimPid")]
    words = []
    for d in dirs:
        path = os.path.join(d, name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                words += [w.strip() for w in f if w.strip() and not w.startswith("#")]
    return words


EN_WORDS = set(w.lower() for w in EN_WORDS_TEXT + _load_extra("words_en.txt"))
TH_WORDS = set(TH_WORDS_TEXT + _load_extra("words_th.txt"))
