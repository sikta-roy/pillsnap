// Offline copy of backend/app/content.py DISPOSAL (used if the API is unreachable).
import type { Disposal } from "./api";
import type { Lang } from "./i18n";

export const fallbackDisposal: Record<Lang, Disposal> = {
  "en": {
    "title": "How to safely throw away old medicines",
    "steps": [
      {
        "title": "Best: use a take-back point",
        "text": "Many pharmacies, hospitals and police stations have medicine drop boxes or take-back days. Ask your local chemist or hospital if they accept old medicines."
      },
      {
        "title": "If there is no take-back point",
        "text": "Take the pills out of the strip or bottle. Mix them with something unpleasant such as used tea leaves, coffee grounds, dirt or cat litter. Do not crush them."
      },
      {
        "title": "Seal it",
        "text": "Put the mix in a sealed plastic bag or a closed container so it cannot leak, and throw it in your household rubbish."
      },
      {
        "title": "Protect your privacy",
        "text": "Scratch out your name and details on prescription labels and boxes before throwing them away."
      }
    ],
    "do_not": [
      "Do not flush medicines down the toilet or sink unless the label says to. They can pollute water.",
      "Do not burn medicines or packs at home.",
      "Do not give your medicines to other people, even if they have similar symptoms.",
      "Do not keep loose pills you cannot identify. When in doubt, throw them out safely."
    ],
    "special": [
      "Needles, syringes and insulin pens: use a hard, closed container (a sharps box) and ask your pharmacy or hospital how to hand it in.",
      "Inhalers and aerosol sprays: do not puncture or burn them. Ask your pharmacy.",
      "Strong painkillers (opioids) are dangerous if someone else takes them. Return them to a take-back point as soon as possible."
    ],
    "source": "Based on US FDA guidance on disposal of unused medicines."
  },
  "hi": {
    "title": "पुरानी दवाओं को सुरक्षित तरीके से कैसे फेंकें",
    "steps": [
      {
        "title": "सबसे अच्छा: दवा वापसी केंद्र",
        "text": "कई फार्मेसी, अस्पताल और थानों में दवा जमा करने के बॉक्स या वापसी दिवस होते हैं। अपने केमिस्ट या अस्पताल से पूछें कि क्या वे पुरानी दवाएँ लेते हैं।"
      },
      {
        "title": "अगर वापसी केंद्र नहीं है",
        "text": "गोलियों को पत्ते या बोतल से निकालें। उन्हें इस्तेमाल की हुई चायपत्ती, कॉफ़ी, मिट्टी या कैट लिटर जैसी किसी अप्रिय चीज़ में मिलाएँ। उन्हें पीसें नहीं।"
      },
      {
        "title": "बंद करें",
        "text": "मिश्रण को बंद प्लास्टिक बैग या ढक्कन वाले डिब्बे में रखें ताकि वह रिसे नहीं, और घर के कूड़े में डाल दें।"
      },
      {
        "title": "अपनी जानकारी सुरक्षित रखें",
        "text": "पर्चे के लेबल और डिब्बों पर लिखा अपना नाम और जानकारी फेंकने से पहले मिटा दें।"
      }
    ],
    "do_not": [
      "जब तक लेबल पर न लिखा हो, दवाएँ टॉयलेट या सिंक में न बहाएँ। इससे पानी प्रदूषित होता है।",
      "घर पर दवाएँ या उनके पैक न जलाएँ।",
      "अपनी दवाएँ किसी और को न दें, भले ही उनके लक्षण मिलते-जुलते हों।",
      "ऐसी खुली गोलियाँ न रखें जिन्हें आप पहचान न सकें। संदेह हो तो उन्हें सुरक्षित तरीके से फेंक दें।"
    ],
    "special": [
      "सुई, सिरिंज और इंसुलिन पेन: सख्त, बंद डिब्बे (शार्प्स बॉक्स) में रखें और फार्मेसी या अस्पताल से पूछें कि उन्हें कहाँ जमा करें।",
      "इनहेलर और एरोसोल स्प्रे: उनमें छेद न करें और न जलाएँ। अपनी फार्मेसी से पूछें।",
      "तेज़ दर्द निवारक (ओपिओइड) किसी और के लेने पर खतरनाक हैं। उन्हें जल्द से जल्द वापसी केंद्र पर लौटाएँ।"
    ],
    "source": "अमेरिकी FDA के अप्रयुक्त दवाओं के निपटान के दिशानिर्देशों पर आधारित।"
  }
};
