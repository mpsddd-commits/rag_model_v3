from src.utils.settings import settings
# html1: 사내 직원 초대
# html2: 컨설턴트 초대 (신규: type 2, 기존: type 3)
# html3: 임시 비밀번호 발송
# html4: 협력사 초대 메일 발송

def html1(companyName, uuid):
    return f"""
      <!DOCTYPE html>
      <html>
      <head>
          <meta charset="UTF-8">
          <title>WITH 서비스 알림</title>
      </head>
      <table width="100%" border="0" cellpadding="0" cellspacing="0" style="padding: 40px 0;">
        <tr>
          <td align="center">
            <table width="600" border="0" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border: 1px solid #eeeeee; border-radius: 12px; overflow: hidden;">
              <tr><td height="5" style="background-color: #28a745;"></td></tr>
              
              <tr>
                <td style="padding: 40px; font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;">
                  <h1 style="font-size:24px; color:#333333; margin-bottom:24px; text-align:center;">
                      ESG 플랫폼 초대 안내
                  </h1>
                  
                  <p style="font-size:16px; color:#333333; line-height:1.6; margin-bottom:20px;">
                    안녕하세요!<br>
                    <strong>{companyName}</strong>의 ESG 데이터 관리 및 협업을 위한<br>
                    <strong>WITH ESG 플랫폼</strong>에 초대되셨습니다.<br>
                    아래 버튼을 클릭하여 회원가입을 완료하고 ESG 업무를 시작해 보세요.
                  </p>
                  <div style="background-color:#f8f9fa; border:1px dashed #03a94d; padding:15px; border-radius:8px; margin:25px 0; text-align:center;">
                    <ul style="margin-bottom: 20px; padding: 0; list-style: none; font-size: 14px; color: #666666;">
                      <li style="margin-bottom: 20px;">
                        <p style="font-size:14px; color:#03a94d; margin-top:0; margin-bottom:10px;"> 소속 회사</p>
                        <span style="font-size:20px; font-weight:bold; letter-spacing:4px; color:#333333; font-family:monospace;"> {companyName}</span>
                      </li>
                      <li style="margin-bottom: 8px;">✔️ 이용 범위: ESG 데이터 관리 및 협업 기능 제공</li>
                      <li>✔️ 가입 절차: 이름, 비밀번호 설정 후 즉시 이용 가능</li>
                    </ul>
                  </div>
                  <div style="text-align: center;">
                    <a href="http://main.{settings.host_ip}/invite/{uuid}" style="background-color: #28a745; color: #ffffff; padding: 16px 40px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block; font-size: 16px;">
                      회원가입 하러가기
                    </a>
                  </div>
                  
                  <p style="font-size: 13px; color: #999999; margin-top: 30px; text-align: center;">
                    본 메일은 초대받은 분께만 발송되었습니다.<br>
                    로그인이 되지 않거나 문제가 발생하면 관리자에게 문의해 주세요.
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
      </html>
    """

def html2(type, companyName, uuid):
    if type == 2:
        consultantHtml = f"""
          <div style="background-color:#ffffff; border:3px solid #03a94d; border-radius:8px; padding:20px;">
              <h3 style="margin:0 0 10px 0; font-size:16px; color:#03a94d;">
                  ✔ 신규 사용자
              </h3>
              <p style="margin:0; font-size:12px; color:#333333; line-height:1.6;">
                  <strong>회원가입 후 ESG 플랫폼에 접속하여</strong> 협업을 시작하실 수 있습니다.
              </p>
          </div>
        """
        url = f"http://main.{settings.host_ip}/invite/{uuid}"
    elif type == 3:
        consultantHtml = f"""
          <div style="background-color:#fff; border:3px solid #03a94d; border-radius:8px; padding:20px; margin-bottom:15px;">
              <h3 style="margin:0 0 10px 0; font-size:16px; color:#03a94d;">
                  ✔ 기존 계정 사용자
              </h3>
              <p style="margin:0; font-size:12px; color:#333333; line-height:1.6;">
                  로그인하면 <strong>ESG 프로젝트 및 데이터 접근 권한이 자동으로 연결됩니다.</strong>
              </p>
          </div>
        """
        url = f"http://{settings.host_ip}/login"
    return f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>WITH 서비스 협업 초대</title>
</head>

<body style="margin:0; padding:40px 0; background-color:#ffffff;">

<table width="100%" border="0" cellpadding="0" cellspacing="0">
    <tr>
        <td align="center">

            <table width="600" border="0" cellpadding="0" cellspacing="0"
                style="background-color:#ffffff; border:1px solid #eeeeee; border-radius:12px; overflow:hidden;">

                <!-- 상단 포인트 -->
                <tr>
                    <td height="5" style="background-color:#03a94d;"></td>
                </tr>

                <tr>
                    <td style="padding:40px; font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;">

                        <h1 style="font-size:22px; color:#333333; margin-bottom:24px; text-align:center;">
                            ESG 플랫폼 협업 초대 안내
                        </h1>

                        <p style="font-size:16px; color:#333333; line-height:1.6; margin-bottom:20px;">
                            귀사를 <strong>{companyName}</strong>의 ESG 프로젝트 협업을 위한<br>
                            <strong>WITH ESG 플랫폼</strong>에 공식 협력사(컨설턴트)로 초대하였습니다.
                        </p>

                        <!-- 안내 박스 -->
                        <div style="background-color:#f8f9fa; border:1px dashed #03a94d; padding:15px; border-radius:8px; margin:25px 0; text-align:center;">
                            <h3 style="margin-top:0; font-size:15px; color:#333333;">
                                [ESG 플랫폼 이용 안내]
                            </h3>
                            <ul style="margin:10px 0 0 0; padding:0; list-style:none; font-size:14px; color:#333333; line-height:1.8;">
                                {consultantHtml}
                            </ul>
                        </div>

                        <p style="font-size:14px; color:#333333; text-align:center; margin-bottom:25px;">
                            원활한 업무 협업을 위해 아래 버튼을 클릭하여 시스템에 접속해 주십시오.
                        </p>

                        <!-- 버튼 -->
                        <div style="text-align:center;">
                            <a href="{url}"
                                style="background-color:#03a94d; color:#ffffff; padding:16px 40px; text-decoration:none; border-radius:6px; font-weight:bold; display:inline-block; font-size:16px;">
                                ESG 플랫폼 접속하기
                            </a>
                        </div>
                        
                        <!-- 안내문 -->
                        <div style="margin-top:40px; padding-top:20px; border-top:1px solid #eeeeee;">
                            <p style="font-size:12px; color:#777777; line-height:1.4; text-align:left;">
                                * 본 메일은 업무 목적으로 발송된 보안 메일입니다.<br>
                                * 시스템 이용 관련 문의: platformanagers@gmail.com
                            </p>
                        </div>

                    </td>
                </tr>

                <!-- 푸터 -->
                <tr>
                    <td style="padding:20px; background-color:#f8f9fa; text-align:center; font-size:12px; color:#888888;">
                        © 2026 WITH Platform. All rights reserved.
                    </td>
                </tr>

            </table>

        </td>
    </tr>
</table>

</body>
</html>
"""

def html3(tempPwd):
  return f"""
  <!DOCTYPE html>
  <html>
  <head>
      <meta charset="UTF-8">
      <title>WITH 서비스 알림</title>
  </head>

  <body style="margin:0; padding:40px 0; background-color:#ffffff;">

  <table width="100%" border="0" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center">

        <table width="600" border="0" cellpadding="0" cellspacing="0"
          style="background-color:#ffffff; border:1px solid #eeeeee; border-radius:12px; overflow:hidden;">

          <!-- 상단 포인트 -->
          <tr>
            <td height="5" style="background-color:#03a94d;"></td>
          </tr>
          
          <tr>
            <td style="padding:40px; font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;">

              <h1 style="font-size:22px; color:#333333; margin-bottom:20px; text-align:center;">
                임시 비밀번호 발급 안내
              </h1>
              
              <p style="font-size:15px; color:#333333; line-height:1.6; text-align:center;">
                안녕하세요<br>
                요청하신 비밀번호 찾기에 따른 임시 비밀번호를 안내해 드립니다.
              </p>

              <!-- 비밀번호 박스 -->
              <div style="background-color:#f8f9fa; border:1px dashed #03a94d; padding:30px; border-radius:8px; margin:25px 0; text-align:center;">
                <p style="font-size:14px; color:#03a94d; margin-top:0; margin-bottom:10px;">
                  임시 비밀번호
                </p>
                <span style="font-size:28px; font-weight:bold; letter-spacing:4px; color:#333333; font-family:monospace;">
                  {tempPwd}
                </span>
              </div>

              <p style="font-size:14px; color:#333333; line-height:1.6; text-align:center; margin-bottom:30px;">
                안전을 위해 로그인 후 <strong>마이페이지 &gt; 비밀번호 변경</strong> 메뉴에서<br>
                반드시 새로운 비밀번호로 변경해 주시기 바랍니다.
              </p>

              <!-- 버튼 -->
              <div style="text-align:center;">
                <a href="http://{settings.host_ip}/login"
                  style="background-color:#03a94d; color:#ffffff; padding:16px 40px; text-decoration:none; border-radius:6px; font-weight:bold; display:inline-block; font-size:16px;">
                  로그인 하러가기
                </a>
              </div>
              
              <!-- 안내문 -->
              <div style="margin-top:40px; padding-top:20px; border-top:1px solid #eeeeee;">
                <p style="font-size:12px; color:#777777; line-height:1.4; text-align:left;">
                  * 본인이 요청하지 않았음에도 이 메일을 받으셨다면, 타인에 의해 계정이 도용되었을 가능성이 있으니 즉시 고객센터로 문의해 주세요.
                </p>
              </div>

            </td>
          </tr>
          
          <!-- 푸터 -->
          <tr>
            <td style="padding:20px; background-color:#f8f9fa; text-align:center; font-size:12px; color:#888888;">
              © 2026 WITH. All rights reserved.
            </td>
          </tr>

        </table>

      </td>
    </tr>
  </table>

  </body>
  </html>
  """


def html5(companyName, authCode):
    """[v1.0] type 5 — 2차 인증 코드 발송 이메일 템플릿"""
    return f"""
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><title>ESG 플랫폼 2차 인증</title></head>
<body style="margin:0; padding:40px 0; background-color:#ffffff;">
<table width="100%" border="0" cellpadding="0" cellspacing="0">
  <tr><td align="center">
    <table width="600" border="0" cellpadding="0" cellspacing="0"
      style="background-color:#ffffff; border:1px solid #eeeeee; border-radius:12px; overflow:hidden;">
      <tr><td height="5" style="background-color:#03a94d;"></td></tr>
      <tr><td style="padding:40px; font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;">
        <h1 style="font-size:22px; color:#333333; margin-bottom:20px; text-align:center;">
          일회용 2차 인증 코드 안내
        </h1>
        <p style="font-size:15px; color:#333333; line-height:1.6; text-align:center;">
          안녕하세요, <strong>{companyName}</strong> 담당자님.<br>
          ESG 공급망 관리 시스템 로그인을 위한<br>
          <strong>일회용 2차 인증 코드</strong>를 안내드립니다.
        </p>
        <div style="background-color:#f8f9fa; border:1px dashed #03a94d; padding:30px; border-radius:8px; margin:25px 0; text-align:center;">
          <p style="font-size:14px; color:#03a94d; margin-top:0; margin-bottom:10px;">인증 코드 (6자리)</p>
          <span style="font-size:36px; font-weight:bold; letter-spacing:8px; color:#333333; font-family:monospace;">
            {authCode}
          </span>
        </div>
        <div style="background-color:#fff3cd; border:1px solid #ffc107; border-radius:8px; padding:15px; margin:20px 0;">
          <p style="font-size:13px; color:#856404; margin:0; line-height:1.5;">
            ⚠️ 본 인증 코드는 <strong>5분간 유효</strong>하며, 1회만 사용 가능합니다.<br>
            타인에게 절대 공유하지 마시기 바랍니다.
          </p>
        </div>
        <p style="font-size:14px; color:#333333; line-height:1.6; text-align:center;">
          로그인 화면으로 돌아가셔서 위 코드를 입력해 주세요.
        </p>
        <div style="margin-top:40px; padding-top:20px; border-top:1px solid #eeeeee;">
          <p style="font-size:12px; color:#777777; line-height:1.4; text-align:left;">
            * 본인이 요청하지 않았음에도 이 메일을 받으셨다면 즉시 관리자에게 문의해 주세요.<br>
            * 문의: platformanagers@gmail.com
          </p>
        </div>
      </td></tr>
      <tr><td style="padding:20px; background-color:#f8f9fa; text-align:center; font-size:12px; color:#888888;">
        © 2026 Triple Values. All rights reserved.
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>
"""


def getHtml(data):
  subject = None
  body = None
  tempPwd = data.get("tempPwd")
  type = data.get("type")
  email = data.get("email")
  if type == 4:
    subject = "임시 비밀번호 발송"
    body = html3(tempPwd)
  elif type == 5:
    subject = "일회용 2차 인증 코드 발급"
    body = html5(data.get("companyName", ""), data.get("authCode", ""))
  return subject, body, email
