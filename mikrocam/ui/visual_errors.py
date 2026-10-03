"""Translate source/recipe boundary failures while keeping diagnostics in a tooltip."""
import builtins
import gettext

_ = getattr(builtins, '_', gettext.gettext)


def visual_error_text(message: str) -> str:
    code = message.partition(':')[0]
    messages = {
        'UNSUPPORTED_SOURCE_FORMAT': _('Desteklenmeyen kaynak biçimi. PNG, JPEG, BMP, TIFF, WebP, GIF, SVG veya PDF seçin.'),
        'SOURCE_TOO_LARGE': _('Dosya bu işlem için belirlenen boyut sınırını aşıyor.'),
        'RASTER_LIMIT_EXCEEDED': _('Bu ölçü ve DPI çok büyük bir görüntü oluşturuyor. Ölçüyü veya DPI’ı azaltın.'),
        'SOURCE_DECODE_FAILED': _('Görsel okunamadı. Dosyanın geçerli olduğundan emin olun.'),
        'SVG_EXTERNAL_RESOURCE': _('SVG harici dosyalara bağlı. Görselleri SVG içine gömerek yeniden kaydedin.'),
        'SVG_UNSUPPORTED_FEATURE': _('SVG’deki bazı öğeler bu sürümde işlenemiyor.'),
        'FONT_MISSING': _('Çizimde kullanılan yazı tipi bulunamadı. Yazı tipini kurun veya metni yola dönüştürün.'),
        'BITMAP_UNAVAILABLE': _('Bu kurulumda resim içe aktarma bileşeni bulunmuyor.'),
        'SVG_UNAVAILABLE': _('Bu kurulumda SVG içe aktarma bileşeni bulunmuyor.'),
        'PDF_UNAVAILABLE': _('Bu kurulumda PDF içe aktarma bileşeni bulunmuyor.'),
        'PDF_PASSWORD_REQUIRED': _('Bu PDF parola korumalı. Parolasız bir kopya seçin.'),
        'PAGE_OUT_OF_RANGE': _('Seçilen sayfa veya kare dosyada bulunmuyor.'),
        'INVALID_GRID': _('Ölçü ve DPI pozitif, geçerli sayılar olmalıdır.'),
        'INVALID_INTERLACE_COUNT': _('Serpiştirme sayısı 1 ile 8 arasında tam sayı olmalıdır.'),
        'RECIPE_VERSION_UNSUPPORTED': _('Bu iş dosyasının sürümü desteklenmiyor. Dosya değiştirilmedi.'),
        'RECIPE_CORRUPT': _('İş dosyasındaki görüntü veya ayarlar doğrulanamadı.'),
        'PLAN_STALE': _('Ayarlar değişti. Maskeyi yeniden hazırlayın.'),
        'PROJECT_ATTACH_FAILED': _('İş projeye eklenemedi. Mevcut işiniz korunuyor.'),
        'CROP_UNSUPPORTED': _('Bu sürüm SVG ve PDF’nin bütün sayfasını kullanır. Kırpılmış bir kaynak seçin.'),
    }
    return messages.get(code, _('İşlem tamamlanamadı. Ayrıntıları görmek için bu metnin üzerine gelin.'))
