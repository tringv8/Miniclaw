import dayjs from "dayjs"
import "dayjs/locale/en"
import "dayjs/locale/vi"
import localizedFormat from "dayjs/plugin/localizedFormat"
import relativeTime from "dayjs/plugin/relativeTime"
import i18n from "i18next"
import LanguageDetector from "i18next-browser-languagedetector"
import { initReactI18next } from "react-i18next"

import en from "./locales/en.json"
import vi from "./locales/vi.json"

dayjs.extend(relativeTime)
dayjs.extend(localizedFormat)

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: {
        translation: en,
      },
      vi: {
        translation: vi,
      },
    },
    fallbackLng: "en",
    debug: false,

    interpolation: {
      escapeValue: false,
    },
  })

i18n.on("languageChanged", (lng) => {
  if (lng.startsWith("vi")) {
    dayjs.locale("vi")
  } else {
    dayjs.locale("en")
  }
})

export default i18n
