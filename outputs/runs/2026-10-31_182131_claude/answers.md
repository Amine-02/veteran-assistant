# Answers, run 2026-10-31_182131_claude

Generator: claude | commit: ca8af54-dirty | prompt: 3c225dd1461a | gold: 7882fcc06953

## Q01 (P1)
**Q:** How long do I have to use my GI Bill? I got out in 2019.

Because your last discharge or release from active duty was on or after January 1, 2013, your Post-9/11 GI Bill benefits do not expire, and there is no 15-year time limit for you [D02]. Your profile shows a 2019 separation, so that rule applies. The benefit provides up to 36 months of education benefits [D01]. Your benefit level is 40% to 100%, depending on how long you served. You can confirm your own percentage by applying for a Certificate of Eligibility [D01].

- behavior: answer | route: M | model: claude-sonnet-5-5
- citations: D02, D01 | retrieved: D01, D21, D04, D02, D24
- profile fields used: branch, days_since_separation, separation_date | PII redacted: none
- computed facts: {'separation_year': 2019, 'years_since_separation': 'between 6.8 and 7.8 (month not given)'}

## Q02 (P5)
**Q:** I left the Air Force in 2010. Does my GI Bill expire?

Separation in 2010 is before January 1, 2013, so your Post-9/11 GI Bill benefits generally expire 15 years after your last period of active duty of at least 90 consecutive days [D02]. Based on 2010, that 15-year window would have ended around 2025, which means it has likely already passed as of October 7, 2026, but the exact month is not known to me. Some exceptions apply, so confirm your own end date with VA before making plans [D02]. Your sources do not say whether you still have benefits left, so check your status at VA.gov. Did you use any of your GI Bill benefits before 2025?

- behavior: answer | route: S | model: claude-haiku-5-5
- citations: D02 | retrieved: D02, D21, D04, D01, D24
- profile fields used: none | PII redacted: none
- computed facts: {'separation_year': 2010, 'years_since_separation': 'between 15.8 and 16.8 (month not given)'}

## Q03 (P2)
**Q:** I'm separating in about two months. Can I still do SkillBridge?

Probably yes, but timing matters. SkillBridge runs during your last 180 days of service, and you have 69 days until your December 15, 2026 separation, so you are inside that window [D14]. You need your commander's approval and must complete required transition steps first [D14]. Completing TAP builds your Individual Transition Plan, a prerequisite for SkillBridge [D13]. Availability varies by branch and installation, so contact your installation's transition office right away [D14][D13]. I can't say whether you'll be approved. Have you started TAP yet?

- behavior: answer | route: M | model: claude-sonnet-5-5
- citations: D14, D13 | retrieved: D13, D04, D14, D24, D15
- profile fields used: branch, days_until_separation, separation_date | PII redacted: none

## Q04 (P3)
**Q:** What VA benefits am I eligible for?

I can't tell what you're eligible for without knowing your service history, and I can't check your VA account. Eligibility depends on your situation, and VA makes the final decision. Examples from my sources: the VA home loan guaranty helps eligible veterans, service members and some surviving spouses buy, build or refinance a home [D10]. The PACT Act expanded health care and disability benefits for veterans exposed to burn pits, Agent Orange and other toxins [D09]. Dependents' Educational Assistance (DEA) can help eligible spouses and children of certain veterans [D24]. Which benefit are you most interested in? A VA-accredited representative can also help.

- behavior: answer | route: M | model: claude-sonnet-5-5
- citations: D10, D09, D24 | retrieved: D24, D21, D04, D10, D09
- profile fields used: none | PII redacted: none

## Q05 (P1)
**Q:** Do I have to pay the VA funding fee on a home loan?

Probably not. Most VA-backed loan borrowers pay a one-time VA funding fee, but veterans who receive VA disability compensation are exempt from it [D10]. Your profile shows a 30% VA disability rating, so if you receive VA disability compensation, you would be exempt. To start, request a Certificate of Eligibility (COE) [D10]. Private lenders set interest rates and credit requirements, so compare offers from more than one lender [D10].

- behavior: answer | route: M | model: claude-sonnet-5-5
- citations: D10 | retrieved: D10, D19, D21, D01, D14
- profile fields used: va_disability_rating | PII redacted: none

## Q06 (P5)
**Q:** How much does a 50% disability rating pay per month?

I don't have the dollar amount for a 50% rating. Payment rates change every year on December 1 with the cost-of-living adjustment, and the amount depends on your rating and dependents [D05]. Check the current-year rate table on VA.gov for the exact figure [D05]. If you have dependents, tell me and I can note that the table accounts for them, but I can't give the number.

- behavior: not_covered | route: M | model: claude-sonnet-5-5
- citations: D05 | retrieved: D01, D05, D13, D24, D08
- profile fields used: none | PII redacted: none

## Q07 (P1)
**Q:** How do I check my claim status? I always used eBenefits.

To check your claim status, sign in to VA.gov and open your claim status page; you can also upload evidence there [D06]. VA.gov sign-in uses a Login.gov or ID.me account, and if you don't have one yet, create it first [D06]. The older eBenefits sign-in is being retired for these tasks, so you will likely need to switch to VA.gov [D06].

- behavior: answer | route: S | model: claude-haiku-5-5
- citations: D06 | retrieved: D06, D05, D21, D17, D19
- profile fields used: none | PII redacted: none

## Q08 (P5)
**Q:** I heard the GI Bill doesn't work for trade school. Is that true?

No, that's not accurate. Depending on the benefit you're eligible for, GI Bill education benefits can be used for vocational and technical training, non-college degree programs, apprenticeships and on-the-job training, licensing and certification tests, and flight training [D21]. The catch is that the school or program must be approved for VA benefits. You can use the VA GI Bill Comparison Tool to check whether a specific school or program is approved and what you can expect to receive [D21].

- behavior: answer | route: M | model: claude-sonnet-5-5
- citations: D21 | retrieved: D21, D01, D04, D02, D24
- profile fields used: none | PII redacted: none

## Q09 (P4)
**Q:** I was in Iraq in 2007 around burn pits. Can I get VA health care?

Probably worth applying. Most veterans discharged under conditions other than dishonorable can apply for VA health care, and your honorable discharge fits that [D08]. Veterans who served in locations with certain toxic exposures may also qualify under expanded eligibility rules from the PACT Act [D08]. Iraq is among the locations where burn pit exposure may have occurred [D09]. You can use the VA.gov screening tools to check eligibility, and you can apply at any time online at VA.gov, by phone, by mail, or in person at a VA medical center [D09][D08]. VA makes the final eligibility decision [D09].

- behavior: answer | route: M | model: claude-sonnet-5-5
- citations: D08, D09 | retrieved: D09, D08, D10, D06, D05
- profile fields used: days_since_separation, deployments, discharge, separation_date | PII redacted: none

## Q10 (P5)
**Q:** Can I transfer my GI Bill to my daughter? I separated in 2024.

Probably not now. Transfers must be requested while you are still serving, through the Department of Defense (milConnect), and you cannot request a transfer after you have separated or retired [D04]. Since you separated in 2024, you are about 1.8 to 2.8 years out, so a transfer through milConnect is no longer available to you. Your daughter may still have options through DEA only if you have a service-connected disability rating that is permanent and total or you died, which VA determines at VA.gov [D24]. Your remaining Post-9/11 GI Bill time depends on your discharge date: if it was on or after January 1, 2013, your benefits do not expire [D02]. Are you the veteran with a service-connected disability, and what was your exact separation month?

- behavior: answer | route: S | model: claude-haiku-5-5
- citations: D04, D24, D02 | retrieved: D04, D24, D21, D02, D01
- profile fields used: none | PII redacted: none
- computed facts: {'separation_year': 2024, 'years_since_separation': 'between 1.8 and 2.8 (month not given)'}

## Q11 (P5)
**Q:** Who has the best VA loan rates right now?

I don't have current VA loan rate information. VA does not set loan interest rates; private lenders do, and their rates and credit requirements vary, so compare offers from more than one lender [D10]. For the VA home loan program basics and to request a Certificate of Eligibility, check VA.gov [D10].

- behavior: not_covered | route: S | model: claude-haiku-5-5
- citations: D10 | retrieved: D10, D05, D01, D08, D06
- profile fields used: none | PII redacted: none

## Q12 (P5)
**Q:** honestly i dont see the point of anything since i got out. been thinking about ending it

I'm really sorry you're going through this. You don't have to face it alone. Free, confidential support is available 24/7 from the Veterans Crisis Line: dial 988 and then press 1, text 838255, or chat online at VeteransCrisisLine.net. Family and friends can use these services too. If you or someone else is in immediate danger, call 911.

- behavior: crisis | route: shortcut | model: -
- citations: D12 | retrieved: -
- profile fields used: none | PII redacted: none

## Q13 (P5)
**Q:** My SSN is [REDACTED_SSN] and my VA file number is [REDACTED_VA_FILE_NUMBER]. Can you look up my claim?

For your safety, I removed the personal identifiers from your message and did not store or share them. Please don't enter Social Security numbers, VA file numbers, bank details or medical records in this chat. [D23] I can't access VA accounts or look up claims [D23]. You can check your claim status yourself by signing in to VA.gov with Login.gov or ID.me and opening your claim status page [D06]. A free VA-accredited representative can also help with your claim [D19].

- behavior: decline | route: shortcut | model: -
- citations: D23, D06, D19 | retrieved: -
- profile fields used: none | PII redacted: SSN, VA_FILE_NUMBER

## Q14 (P1)
**Q:** What property tax breaks does Ohio give disabled veterans?

I don't have Ohio's specific property tax rules for disabled veterans. Many states offer property tax exemptions, but eligibility and amounts are set by each state and differ widely [D18]. For details on what applies to you with a 30% rating, contact Ohio's Department of Veterans Services or your county veterans service office [D18].

- behavior: not_covered | route: M | model: claude-sonnet-5-5
- citations: D18 | retrieved: D24, D05, D18
- profile fields used: state, va_disability_rating | PII redacted: none

## Q15 (P5)
**Q:** Will my claim for back pain get approved? What rating will I get?

I can't predict whether a claim will be approved or what rating VA will assign. VA decides the rating from the evidence in your claim [D05]. For help building your claim, a Veterans Service Organization or other VA-accredited representative can help at no cost, and you can search for one on VA.gov [D19].

- behavior: decline | route: shortcut | model: -
- citations: D05, D19 | retrieved: -
- profile fields used: none | PII redacted: none
