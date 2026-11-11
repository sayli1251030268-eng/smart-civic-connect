import { useState, useEffect } from 'react';

export const DICTIONARY = {
  en: {
    app_title: "Smart Civic Connect",
    issues_near_you: "Issues near you",
    dev_updates: "Development updates",
    my_portal: "My portal",
    dashboard: "Dashboard",
    notifications: "Updates",
    report_issue: "Report an issue",
    login: "Log in",
    logout: "Log out",
    register: "Register",
    feed_title: "What's broken around you",
    feed_subtitle: "Back an issue if you face it too. More support moves it up the municipal priority list.",
    all_categories: "All categories",
    tab_nearby: "Nearby",
    tab_trending: "Most supported",
    tab_all: "Latest",
    tab_mine: "My reports",
    tab_following: "Following",
    support_btn: "I face this too",
    supporting_btn: "Supporting",
    like_btn: "Like",
    repost_btn: "Repost",
    comments_btn: "Comments",
    follow_btn: "Follow",
    following_btn: "Following",
    share_whatsapp: "Share on WhatsApp",
    view_receipt: "Citizen Receipt",
    report_abuse: "Report Abuse",
    sla_breached: "SLA Breached / Urgent",
    sla_left: "SLA remaining",
    anonymous_reporter: "Anonymous Resident",
    pothole: "Pothole",
    garbage: "Garbage Overflow",
    streetlight: "Broken Streetlight",
    water_leakage: "Water Leakage",
    drainage: "Drainage & Sewage",
    other: "Other Issue",
  },
  mr: {
    app_title: "स्मार्ट सिव्हिक कनेक्ट",
    issues_near_you: "तुमच्या परिसरातील समस्या",
    dev_updates: "विकास कार्ये",
    my_portal: "माझे पोर्टल",
    dashboard: "डॅशबोर्ड",
    notifications: "अपडेट्स",
    report_issue: "तक्रार नोंदवा",
    login: "लॉग इन",
    logout: "लॉग आउट",
    register: "नोंदणी करा",
    feed_title: "तुमच्या परिसरातील नागरी समस्या",
    feed_subtitle: "जर तुम्हालाही ही अडचण येत असेल तर पाठिंबा द्या. जास्त पाठिंब्यामुळे महापालिका त्वरित दखल घेईल.",
    all_categories: "सर्व प्रकार",
    tab_nearby: "जवळपासच्या",
    tab_trending: "सर्वाधिक पाठिंबा",
    tab_all: "नवीनतम",
    tab_mine: "माझ्या तक्रारी",
    tab_following: "मी फॉलो केलेल्या",
    support_btn: "मलाही ही समस्या आहे",
    supporting_btn: "पाठिंबा दिला",
    like_btn: "पसंत करा",
    repost_btn: "पुन्हा शेअर करा",
    comments_btn: "टिप्पण्या",
    follow_btn: "फॉलो करा",
    following_btn: "फॉलो करत आहे",
    share_whatsapp: "व्हॉट्सॲपवर शेअर करा",
    view_receipt: "तक्रार पावती",
    report_abuse: "तक्रार नोंदवा (गैरवापर)",
    sla_breached: "मुदत संपली / तातडीचे",
    sla_left: "शिल्लक वेळ",
    anonymous_reporter: "अनामित नागरिक",
    pothole: "रस्त्यावरील खड्डा",
    garbage: "कचऱ्याचे ढीग",
    streetlight: "बंद पथदिवा",
    water_leakage: "पाण्याची गळती",
    drainage: "ड्रेनेज व सांडपाणी",
    other: "इतर समस्या",
  },
  hi: {
    app_title: "स्मार्ट सिविक कनेक्ट",
    issues_near_you: "आपके आस-पास की समस्याएं",
    dev_updates: "विकास कार्य",
    my_portal: "मेरा पोर्टल",
    dashboard: "डैशबोर्ड",
    notifications: "अपडेट्स",
    report_issue: "शिकायत दर्ज करें",
    login: "लॉग इन",
    logout: "लॉग आउट",
    register: "पंजीकरण करें",
    feed_title: "आपके आस-पास की नागरिक समस्याएं",
    feed_subtitle: "अगर आप भी इस समस्या का सामना कर रहे हैं तो समर्थन दें। अधिक समर्थन से समस्या जल्दी सुलझती है।",
    all_categories: "सभी श्रेणियां",
    tab_nearby: "आस-पास",
    tab_trending: "सर्वाधिक समर्थित",
    tab_all: "नवीनतम",
    tab_mine: "मेरी शिकायतें",
    tab_following: "फॉलो की गई",
    support_btn: "मुझे भी यह समस्या है",
    supporting_btn: "समर्थन दिया",
    like_btn: "पसंद करें",
    repost_btn: "रीपोस्ट करें",
    comments_btn: "टिप्पणियां",
    follow_btn: "फॉलो करें",
    following_btn: "फॉलो कर रहे हैं",
    share_whatsapp: "व्हाट्सएप पर शेयर करें",
    view_receipt: "नागरिक रसीद",
    report_abuse: "दुरुपयोग की रिपोर्ट",
    sla_breached: "समय सीमा समाप्त / जरूरी",
    sla_left: "बचा हुआ समय",
    anonymous_reporter: "अज्ञात नागरिक",
    pothole: "सड़क का गड्ढा",
    garbage: "कचरे का ढेर",
    streetlight: "टूटी स्ट्रीटलाइट",
    water_leakage: "पानी का रिसाव",
    drainage: "सीवरेज व नाली",
    other: "अन्य समस्या",
  }
};

let currentLang = localStorage.getItem('scc_lang') || 'en';
const listeners = new Set();

export function setLanguage(lang) {
  if (DICTIONARY[lang]) {
    currentLang = lang;
    localStorage.setItem('scc_lang', lang);
    listeners.forEach((fn) => fn(lang));
  }
}

export function getLanguage() {
  return currentLang;
}

export function useTranslation() {
  const [lang, setLang] = useState(currentLang);
  useEffect(() => {
    listeners.add(setLang);
    return () => listeners.delete(setLang);
  }, []);

  const t = (key) => DICTIONARY[lang]?.[key] || DICTIONARY.en[key] || key;
  return { t, lang, setLanguage };
}
