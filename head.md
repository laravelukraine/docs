---
git: 8042e4ce5c44b0ad51476cb1fb915af086047edb
---
# Laravel Head

- [Вступ](#introduction)
- [Встановлення](#installation)
- [Швидкий старт](#quickstart)
- [Пріоритет розв'язання](#resolution-precedence)
- [Визначення метаданих](#defining-metadata)
    - [Значення за замовчуванням](#defaults)
    - [Метадані маршруту](#route-metadata)
    - [Метадані під час виконання](#runtime-metadata)
    - [Сторінки помилок](#error-pages)
- [Open Graph](#open-graph)
    - [Картки X / Twitter](#twitter-cards)
- [Кольори теми](#theme-colors)
- [Метадані застосунку та іконки](#app-metadata-and-icons)
- [Прогресивні вебзастосунки](#progressive-web-apps)
- [Продуктивність і виявлення](#performance-and-discovery)
- [Власні теги](#custom-tags)
- [Схеми](#schemas)
    - [Хлібні крихти](#breadcrumbs)
    - [Часті питання](#faqs)
    - [Власні схеми](#custom-schemas)
- [Рендеринг](#rendering)
    - [Blade](#blade)
    - [Livewire](#livewire)
    - [Inertia](#inertia)

<a name="introduction"></a>
## Вступ

[Laravel Head](https://github.com/laravel/head) надає плавний API для керування елементом `<head>` документа вашого застосунку: заголовком і мета-тегами, метаданими Open Graph, канонічними URL, директивами для роботів, підказками продуктивності та структурованими даними. Він працює з Blade, Livewire та Inertia.

<a name="installation"></a>
## Встановлення

Laravel Head встановлюється через менеджер пакетів Composer:

```shell
composer require laravel/head
```

<a name="quickstart"></a>
## Швидкий старт

Зареєструйте загальносайтові значення за замовчуванням у сервіс-провайдері:

```php
use Laravel\Head\Facades\Head;
use Laravel\Head\HeadBuilder;

Head::defaults(fn (HeadBuilder $head) => $head
    ->title('Laravel', suffix: ' - Laravel')
    ->description('Build something great.'));
```

Задайте метадані конкретної сторінки під час виконання:

```php
Head::title($post->title)
    ->description($post->description);
```

Відрендеріть розв'язані теги у своєму макеті:

```blade
<head>
    @head
</head>
```

<a name="resolution-precedence"></a>
## Пріоритет розв'язання

Метадані сторінки розв'язуються з п'яти шарів, наведених від найнижчого пріоритету до найвищого:

1. Значення сторінки за замовчуванням
2. Метадані групи маршрутів
3. Метадані маршруту
4. Метадані під час виконання
5. Метадані помилки

Вищі шари заміщують нижчі поле за полем. Наприклад, заголовок, заданий під час виконання, заміщує заголовок маршруту, не чіпаючи його опис. Розділи нижче описують, як задати метадані на кожному шарі. Про рендеринг розв'язаних метаданих у Blade, Livewire та Inertia читайте в розділі [Рендеринг](#rendering).

<a name="defining-metadata"></a>
## Визначення метаданих

Laravel Head дозволяє визначати метадані через загальносайтові значення за замовчуванням, метадані маршруту, виклики під час виконання та визначення для сторінок помилок.

<a name="defaults"></a>
### Значення за замовчуванням

Зареєструйте значення сторінки за замовчуванням у сервіс-провайдері:

```php
use Laravel\Head\Enums\OgType;
use Laravel\Head\Facades\Head;
use Laravel\Head\HeadBuilder;

Head::defaults(function (HeadBuilder $head) {
    $head
        ->title('Laravel', suffix: ' - Laravel')
        ->description('Build something great.')
        ->canonical()
        ->og(siteName: 'Laravel', type: OgType::Website)
        ->searchableByRobots()
        ->preconnect('https://fonts.example.com');
});
```

Значення за замовчуванням - найнижчий шар метаданих сторінки. Якщо жоден маршрут, виклик під час виконання чи метадані помилки не задають заголовка, `Laravel` рендериться як є. Коли заголовок сторінки задає вищий шар, успадкований суфікс застосовується, тож `Head::title('About')` відрендерить `About - Laravel`. Передайте `exact: true` для заголовків, які мають ігнорувати успадкований префікс або суфікс.

Виклик `Head::canonical()` рендерить канонічний URL на основі URL поточного запиту. Щоб задати URL явно, передайте рядок, наприклад `Head::canonical('/about')`. Канонічні URL за замовчуванням нормалізуються до `https`; передайте `forceHttps: false`, щоб зберегти схему запиту.

Директиви для роботів можна передати сирим рядком, як case-и енума `RobotsRule` або списком, що змішує обидві форми. Списки рендеряться як директиви через кому, тож `Head::robots([RobotsRule::NoIndex, RobotsRule::NoFollow])` дає `noindex, nofollow`.

Для зручності метод `searchableByRobots` рендерить `all`, а метод `hiddenFromRobots` - `none`.

<a name="route-metadata"></a>
### Метадані маршруту

Ви можете визначати метадані безпосередньо на маршрутах - це особливо зручно для напівстатичних сторінок, метадані яких відомі заздалегідь.

<a name="routes-and-groups"></a>
#### Маршрути та групи

```php
Route::view('/contact', 'contact')
    ->name('contact')
    ->withHead(
        title: 'Contact Us',
        description: 'Get in touch.',
    );
```

Спільні метадані маршрутів можна застосувати до групи в будь-якій позиції ланцюжка:

```php
Route::withHead(robots: 'noindex, nofollow')
    ->prefix('admin')
    ->name('admin.')
    ->group(function () {
        Route::get('/dashboard', DashboardController::class)
            ->name('dashboard')
            ->withHead(title: 'Dashboard');
    });
```

Метадані можна визначати також для ресурсних і одиничних маршрутів:

```php
Route::resource('posts', PostController::class)->withHead(
    robots: 'index, follow',
);

Route::singleton('profile', ProfileController::class)->withHead(
    title: 'Your Profile',
);
```

Метод `withHead` зберігає звичайні масиви через нативний API метаданих маршрутів Laravel. Він рівнозначний виклику методу `metadata` з атрибутами, вкладеними під ключ `head`, тож метадані лишаються сумісними з кешованими маршрутами.

Іменовані аргументи навмисно обмежені вбудованими властивостями маршрутів Laravel Head, щоб редактори та статичний аналіз ловили помилки в назвах. Атрибути маршрутів, зареєстровані власними білдерами тегів, передаються через `extensions`:

```php
Route::get('/article', ArticleController::class)->withHead(
    title: 'Article',
    extensions: ['readingTime' => 4],
);
```

<a name="supported-properties"></a>
#### Підтримувані властивості

Підтримувані властивості маршруту мають ті самі назви, що й методи плавного білдера:

| Категорія | Властивості |
| --- | --- |
| Документ | `title`, `description`, `canonical`, `robots` |
| Метадані застосунку | `themeColor`, `applicationName`, `colorScheme`, `referrer`, `viewport`, `appleWebAppTitle`, `webAppCapable`, `appleWebAppStatusBarStyle` |
| Соціальні мережі | `og`, `ogImage`, `ogVideo`, `ogAudio`, `twitter`, `twitterImage` |
| Продуктивність | `preload`, `prefetch`, `preconnect`, `dnsPrefetch` |
| Виявлення | `alternates`, `feed`, `icon`, `favicon`, `appleTouchIcon`, `appleTouchStartupImage`, `maskIcon`, `manifest` |
| Структуровані дані | `schema` |
| Власні теги | `meta`, `link` |

Назви вкладених опцій використовують той самий `camelCase`, що й плавний API, наприклад `forceHttps`, `siteName` і `secureUrl`.

Повторювані властивості - `ogImage`, `preload`, `feed`, `schema`, `icon` та `appleTouchStartupImage` - приймають або одне значення, або список.

<a name="runtime-metadata"></a>
### Метадані під час виконання

Коли значення невідоме до надходження запиту - наприклад, заголовок допису, який переглядають, - його можна задати під час виконання:

```php
use Laravel\Head\Facades\Head;

public function __invoke(Post $post): Response
{
    Head::title($post->title);

    // ...
}
```

Виклики під час виконання через фасад `Head` перекривають метадані маршруту для даних, що залежать від запиту. Найчастіше такі виклики роблять у контролерах і діях:

```php
use App\Models\Post;
use Laravel\Head\Facades\Head;

public function show(Post $post)
{
    Head::title($post->title)
        ->description($post->description);

    return view('posts.show', ['post' => $post]);
}
```

Кілька викликів під час виконання зливаються в порядку їх виконання. Для полів з одним значенням - заголовка, опису, канонічного URL і директив для роботів - перемагає пізніший виклик. Повторювані поля зберігають кілька записів, але повторне додавання того самого ключа оновлює попередній запис. Для методу `ogImage` ключем є URL:

```php
Head::ogImage('/images/cover.jpg', alt: 'Draft cover')
    ->ogImage('/images/gallery.jpg', alt: 'Gallery image')
    ->ogImage('/images/cover.jpg', alt: 'Final cover', width: 1200, height: 630);
```

```html
<meta property="og:image" content="/images/cover.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Final cover">
<meta property="og:image" content="/images/gallery.jpg">
<meta property="og:image:alt" content="Gallery image">
```

Медіа Open Graph, успадковані зі значень за замовчуванням, працюють як запасний варіант. Коли метадані маршруту, виконання чи помилки визначають власне медіа того самого типу, медіа за замовчуванням заміщується, а не зливається, тож `og:image` сторінки має перевагу над загальносайтовим зображенням.

Умовні метадані визначаються плавно через методи `when` та `unless`:

```php
Head::title($post->title)
    ->when($post->isDraft(), fn ($head) => $head->hiddenFromRobots());
```

<a name="error-pages"></a>
### Сторінки помилок

Зазвичай метадані помилок реєструють у методі `boot` класу `AppServiceProvider` вашого застосунку:

```php
use Laravel\Head\ErrorPages;
use Laravel\Head\Facades\Head;

/**
 * Bootstrap any application services.
 */
public function boot(): void
{
    Head::errors(function (ErrorPages $errors) {
        $errors->defaults(robots: 'noindex, follow');

        $errors->status(
            404,
            title: 'Page Not Found',
            description: 'The page you are looking for could not be found.',
        );
    });
}
```

Методи `defaults` і `status` також приймають той самий колбек плавного білдера, що й `Head::defaults()`:

```php
use Laravel\Head\ErrorPages;
use Laravel\Head\Facades\Head;
use Laravel\Head\HeadBuilder;

Head::errors(function (ErrorPages $errors) {
    $errors->status(404, fn (HeadBuilder $head) => $head
        ->title('Page Not Found')
        ->description('The page you are looking for could not be found.'));
});
```

Коли відповідь рендериться для зареєстрованого статусу помилки, ці метадані мають перевагу над усіма іншими шарами.

Laravel автоматично визначає статус відповіді під час рендерингу представлення помилки або виконання хука фази відповіді, як-от метод `handleExceptionsUsing()` з Inertia. Якщо ви рендерите відповідь з помилкою всередині колбека `$exceptions->render()`, викличте `Head::status(404)` перед рендерингом, щоб метадані помилки застосувалися.

<a name="open-graph"></a>
## Open Graph

Властивості Open Graph задаються методом `og`. Повторюване медіа додається методами верхнього рівня, які приймають іменовані аргументи напряму:

```php
use Laravel\Head\Enums\ImageType;
use Laravel\Head\Enums\OgType;

Head::og(type: OgType::Article, title: $post->title)
    ->ogImage($post->hero_image_url)
    ->ogImage(
        $post->gallery_image_url,
        alt: $post->gallery_image_alt,
        width: 1200,
        height: 630,
        type: ImageType::Jpeg,
    );
```

Методи `ogImage`, `ogVideo` та `ogAudio` приймають URL першим аргументом, а також необов'язкові іменовані аргументи, як-от `alt`, `width`, `height`, `type` і `secureUrl` - там, де їх підтримує специфікація Open Graph.

MIME-типи зображень можна передавати як case-и енума `ImageType` усюди, де API приймає `type` зображення: `ImageType::Svg`, `ImageType::Png`, `ImageType::Jpeg` та `ImageType::Webp`.

> [!NOTE]
> `title` і `description` документа автоматично заповнюють відсутні значення `og:title` та `og:description`.

Для одного зображення Open Graph без інших атрибутів можна передати іменований аргумент `image` до методу `og`:

```php
Head::og(
    type: OgType::Website,
    title: $page->title,
    description: $page->description,
    image: $page->og_image_url,
);
```

Виклики `og(image: ...)` та `ogImage(...)` пишуть в один і той самий список зображень, тож користуйтеся тим, що виразніше в конкретному місці. Для власних розширень Open Graph, як-от властивостей товару чи статті, скористайтеся методом [`meta`](#custom-tags).

<a name="twitter-cards"></a>
### Картки X / Twitter

Щоб рендерити картки X / Twitter з того самого заголовка, опису та зображення, що й Open Graph, зареєструйте `twitter()` у значеннях за замовчуванням:

```php
use Laravel\Head\Enums\TwitterCard;
use Laravel\Head\Facades\Head;
use Laravel\Head\HeadBuilder;

Head::defaults(fn (HeadBuilder $head) => $head->twitter(
    card: TwitterCard::SummaryWithLargeImage,
));
```

Потім задайте метадані рівня сторінки:

```php
Head::title('Introducing Laravel Head')
    ->description('A fluent API for Laravel document head metadata.')
    ->ogImage('https://example.com/social.jpg', alt: 'Introducing Laravel Head');
```

Це відрендерить відповідні теги Twitter:

```html
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Introducing Laravel Head">
<meta name="twitter:description" content="A fluent API for Laravel document head metadata.">
<meta name="twitter:image" content="https://example.com/social.jpg">
<meta name="twitter:image:alt" content="Introducing Laravel Head">
```

Окремі сторінки можна налаштувати явними значеннями Twitter:

```php
Head::twitter(title: $post->social_title)
    ->twitterImage($post->social_image_url, alt: $post->title);
```

Метадані маршруту приймають `twitter` і `twitterImage`.

<a name="theme-colors"></a>
## Кольори теми

Кольори теми задаються глобально, для маршруту або під час виконання:

```php
Head::themeColor('#0f172a');
```

Це рендерить тег `<meta name="theme-color">`. Для кольорів теми, прив'язаних до медіа, скористайтеся енумом `Media`:

```php
use Laravel\Head\Enums\Media;

Head::themeColor('#ffffff', media: Media::Light)
    ->themeColor('#111827', media: Media::Dark);
```

Енум `Media` містить також `Portrait` і `Landscape`. Аргумент `media` приймає й власний рядок медіазапиту.

Метадані маршруту підтримують один колір теми через той самий ключ у `camelCase`:

```php
Route::view('/dashboard', 'dashboard')->withHead(
    themeColor: '#0f172a',
);
```

<a name="app-metadata-and-icons"></a>
## Метадані застосунку та іконки

Laravel Head містить методи для поширених метаданих браузера та застосунку:

```php
use Laravel\Head\Enums\ImageType;
use Laravel\Head\Enums\Media;

Head::applicationName('Laravel')
    ->colorScheme('light dark')
    ->referrer('strict-origin-when-cross-origin')
    ->viewport('width=device-width, initial-scale=1')
    ->appleWebAppTitle('Laravel')
    ->webAppCapable()
    ->appleWebAppStatusBarStyle('black')
    ->favicon('/favicon.svg', type: ImageType::Svg)
    ->icon('/favicon-32x32.png', type: ImageType::Png, sizes: '32x32')
    ->appleTouchIcon('/apple-touch-icon.png', sizes: '180x180')
    ->appleTouchStartupImage('/launch.png', media: Media::Portrait)
    ->maskIcon('/safari-pinned-tab.svg', color: '#111827')
    ->manifest('/site.webmanifest');
```

Метод `favicon` - псевдонім методу `icon` і приймає ті самі аргументи `type`, `sizes` та `media`.

Метадані маршруту використовують ті самі назви:

```php
use Laravel\Head\Enums\ImageType;
use Laravel\Head\Enums\Media;

Route::view('/dashboard', 'dashboard')->withHead(
    applicationName: 'Laravel',
    colorScheme: 'light dark',
    appleWebAppTitle: 'Laravel',
    webAppCapable: true,
    appleWebAppStatusBarStyle: 'black',
    favicon: [
        ['href' => '/favicon.svg', 'type' => ImageType::Svg],
        ['href' => '/favicon-32x32.png', 'type' => ImageType::Png, 'sizes' => '32x32'],
    ],
    appleTouchIcon: ['href' => '/apple-touch-icon.png', 'sizes' => '180x180'],
    appleTouchStartupImage: ['href' => '/launch.png', 'media' => Media::Portrait],
    manifest: '/site.webmanifest',
);
```

<a name="progressive-web-apps"></a>
## Прогресивні вебзастосунки

Метод `pwa` налаштовує поширені теги `<head>`, потрібні для вебзастосунку, який можна встановити:

```php
Head::pwa(
    name: 'Laravel',
    manifest: '/site.webmanifest',
    themeColor: '#0f172a',
    appleTouchIcon: '/apple-touch-icon.png',
    appleWebAppStatusBarStyle: 'black',
);
```

Це рендерить назву застосунку, посилання на маніфест вебзастосунку та метадані автономного режиму для iOS. Якщо їх передано, рендеряться також колір теми, стиль рядка стану Apple та іконка Apple touch. Створення маніфесту вебзастосунку й реєстрація service worker лишаються відповідальністю вашого застосунку.

Метод `pwa` можна використовувати у значеннях за замовчуванням або метаданих під час виконання. Метадані маршруту підтримують окремі властивості, показані вище.

<a name="performance-and-discovery"></a>
## Продуктивність і виявлення

Laravel Head рендерить підказки продуктивності, посилання пагінації, локальні альтернативи та виявлення стрічок:

```php
Head::preload(asset('fonts/inter.woff2'), as: 'font', crossorigin: true)
    ->prefetch(asset('images/next.webp'))
    ->preconnect('https://cdn.example.com')
    ->dnsPrefetch('https://analytics.example.com')
    ->paginate($posts)
    ->alternates([
        'en' => 'https://example.com/en/about',
        'fr' => 'https://example.com/fr/about',
        'x-default' => 'https://example.com/about',
    ])
    ->feed('/feed', title: 'Laravel RSS')
    ->feed('/feed.atom', type: 'atom', title: 'Laravel Atom');
```

Для локальних ресурсів `preloadAsset()` і `prefetchAsset()` розв'язують URL через хелпер `asset()` і визначають атрибут `as` за розширенням файлу. Попереднє завантаження шрифтів автоматично додає `crossorigin`, якого специфікація preload вимагає навіть для шрифтів того самого джерела:

```php
Head::preloadAsset('fonts/inter.woff2')
    ->prefetchAsset('images/next.webp');
```

```html
<link rel="preload" href="https://example.com/fonts/inter.woff2" as="font" crossorigin>
<link rel="prefetch" href="https://example.com/images/next.webp" as="image">
```

Атрибут `as` можна передати явно, щоб перекрити автовизначення. Метод `preloadAsset` кине виняток, коли атрибут `as` не вдається визначити за розширенням, бо браузери ігнорують preload без цього атрибута; метод `prefetchAsset` просто його опустить.

<a name="custom-tags"></a>
## Власні теги

Для тегів без окремого методу скористайтеся `meta()` та `link()`:

```php
Head::meta('format-detection', 'telephone=no')
    ->meta('article:author', $post->author->name)
    ->link('search', '/opensearch.xml', [
        'type' => 'application/opensearchdescription+xml',
        'title' => 'Laravel Search',
    ])
    ->link('me', 'https://social.example.com/@laravel');
```

До мета-тега можна додати медіазапит, коли браузер має застосовувати тег лише за відповідних умов:

```php
use Laravel\Head\Enums\Media;

Head::meta('theme-color', '#ffffff', media: Media::Light)
    ->meta('theme-color', '#111827', media: Media::Dark);
```

Метод `meta` використовує атрибут `name` для звичайних мета-тегів. Для ключів, які зазвичай вживають атрибут `property` - як-от Open Graph (`og:`) чи метадані статті (`article:`), - метод перемикається автоматично:

```php
Head::meta('description', 'About Laravel')
    ->meta('og:title', 'About Laravel');
```

```html
<meta name="description" content="About Laravel">
<meta property="og:title" content="About Laravel">
```

Щоб обрати атрибут явно, передайте `property: true` або `property: false`.

<a name="schemas"></a>
## Схеми

Вбудовані білдери схем покривають поширені типи JSON-LD:

```php
use Laravel\Head\Enums\OfferAvailability;
use Laravel\Head\Facades\Schema;

Head::schema(
    Schema::product()
        ->name($product->name)
        ->offers(
            Schema::offer()
                ->price($product->price)
                ->currency('USD')
                ->availability(OfferAvailability::InStock)
        )
);
```

Вбудовані фабричні методи - `article`, `blogPosting`, `product`, `offer`, `brand`, `breadcrumbs`, `faq`, `organization`, `person`, `webPage` та `webSite`. Невідомі фабричні методи створюють узагальнений об'єкт схеми, тож ви все одно можете виразити власні типи schema.org.

Коли дані схеми JSON-LD некоректні, Laravel Head кидає виняток у непродакшн-середовищах і пише попередження в лог на продакшні.

<a name="breadcrumbs"></a>
### Хлібні крихти

Елементи хлібних крихт додаються по одному або пакетом. Позиції призначаються автоматично в порядку додавання:

```php
Head::schema(
    Schema::breadcrumbs()->items([
        'Home' => route('home'),
        'Shop' => route('shop.index'),
        'Shoes' => route('shop.category', 'shoes'),
    ])
);
```

Щоб додати одну хлібну крихту, скористайтеся методом `item`:

```php
Schema::breadcrumbs()
    ->item('Home', route('home'))
    ->item('Shop', route('shop.index'));
```

<a name="faqs"></a>
### Часті питання

Записи FAQ працюють за тим самим принципом. Додавайте їх по одному методом `question` або пакетом методом `questions`:

```php
Head::schema(
    Schema::faq()->questions([
        'What is Laravel Head?' => 'A fluent API for managing the document head.',
        'Is it free?' => 'Yes, it is open source.',
    ])
);
```

<a name="custom-schemas"></a>
### Власні схеми

Власні типи схем можна зареєструвати явно:

```php
use DateTimeInterface;
use Laravel\Head\Facades\Schema;
use Laravel\Head\Schema\SchemaObject;
use Laravel\Head\SchemaType;

#[SchemaType('JobPosting')]
class JobPosting extends SchemaObject
{
    public function title(string $title): static
    {
        return $this->set('title', $title);
    }

    public function datePosted(DateTimeInterface|string $date): static
    {
        return $this->date('datePosted', $date);
    }
}

Schema::register(JobPosting::class);

Head::schema(
    Schema::jobPosting()
        ->title('Senior Laravel Developer')
        ->datePosted(now())
);
```

<a name="rendering"></a>
## Рендеринг

Laravel Head розв'язує метадані сторінки в теги для поточної відповіді. Те, як ці теги рендеряться, залежить від стека вашого застосунку.

HTML-рендерер живить директиву `@head` і відрендерені елементи, якими Laravel Head ділиться з Inertia через проп `head`. Рендерер масиву живить `Head::toArray()` для застосунків, яким потрібні розв'язані метадані у вигляді структурованих даних.

<a name="blade"></a>
### Blade

Рендеріть накопичені теги в `<head>` свого макета директивою `@head`:

```blade
<head>
    <meta charset="utf-8">
    @head
</head>
```

Директива `@head` рендериться синхронно, тому метадані сторінки слід визначати до рендерингу макета.

<a name="livewire"></a>
### Livewire

Застосунки на Livewire використовують ту саму директиву `@head` у макеті документа:

```blade
<head>
    @head
</head>

<body>
    {{ $slot }}

    @livewireScripts
</body>
```

Жодних специфічних для Livewire налаштувань не потрібно. Метадані Laravel Head розв'язуються на кожен запит, а резолвер має область видимості запиту. Тому кожен перехід через `wire:navigate` завантажує свіжий документ, вивід `@head` якого відповідає метаданим маршруту призначення. Сторінки, відвідані через `wire:navigate`, отримують належні метадані маршруту, виконання та помилок без коду для head на рівні компонента.

<a name="inertia"></a>
### Inertia

Використовуйте ту саму директиву `@head` у кореневому шаблоні Inertia, поруч із власними компонентами Inertia:

```blade
<html>
<head>
    <meta charset="utf-8">
    @head

    @viteReactRefresh
    @vite(['resources/css/app.css', 'resources/js/app.tsx'])
    <x-inertia::head />
</head>
<body>
    <x-inertia::app />
</body>
</html>
```

Коли Inertia встановлено, Laravel Head автоматично ділиться керованим сторінкою head як масивом відрендерених рядків елементів під пропом `head` у кожному об'єкті сторінки:

```json
{
    "props": {
        "head": [
            "<title data-inertia=\"title\">Dashboard - Laravel</title>",
            "<meta data-inertia=\"description\" name=\"description\" content=\"Your application overview.\">"
        ]
    }
}
```

Увімкніть опцію `serverHead` в Inertia там, де ваш застосунок викликає `createInertiaApp()`. Опція доступна в Inertia 3.5 і новіших:

```js
createInertiaApp({
    // ...
    serverHead: true,
});
```

Кожен керований сторінкою елемент має стабільний ключ `data-inertia`. Директива `@head` рендерить початковий документ, після чого Inertia переймає ці елементи й тримає їх синхронізованими під час звичайних переходів, [миттєвих переходів](https://inertiajs.com/docs/v3/the-basics/instant-visits) і навігації вперед-назад. Елементи присутні в початковій HTML-відповіді, тож пошукові краулери й боти попереднього перегляду посилань читають їх без виконання JavaScript. Клієнтський компонент `<Head>` не потрібен.

Це працює як із [рендерингом на боці сервера (SSR)](https://inertiajs.com/docs/v3/advanced/server-side-rendering), так і без нього. Якщо ваш застосунок має окрему точку входу для SSR, увімкніть `serverHead` і там. Laravel Head автоматично усуває дублікати керованих сторінкою елементів між `@head` і `<x-inertia::head />` незалежно від їхнього порядку, зберігаючи інші елементи head, створені JavaScript-SSR.

> [!NOTE]
> Додаючи Laravel Head до наявного застосунку на Inertia, приберіть будь-які колбеки заголовка з `resources/js/app.tsx` і `resources/js/ssr.tsx`, щоб Laravel Head керував остаточним заголовком документа, і перенесіть теги, якими керує [компонент `<Head>`](https://inertiajs.com/docs/v3/the-basics/title-and-meta) з Inertia, до Laravel Head, щоб вони ніколи не визначали той самий елемент удвох.

Проп `head` не входить до відповідей часткового перезавантаження, тож Inertia зберігає head останньої повної сторінки. Миттєві переходи так само зберігають поточний head, доки не надійде фонова відповідь. Якщо ваш застосунок уже використовує проп `head`, змініть його назву в сервіс-провайдері:

```php
use Laravel\Head\Facades\Head;

public function boot(): void
{
    Head::inertia(prop: '_head');
}
```

Потім вкажіть Inertia той самий проп через `serverHead: '_head'`.

<a name="static-inertia-tags"></a>
#### Статичні теги Inertia

Більшість тегів мають жити у значеннях за замовчуванням, метаданих маршруту чи метаданих під час виконання, щоб Laravel Head розв'язував правильне значення для кожної сторінки. Глобальні значення Inertia використовуйте лише для тегів документа, які рендеряться в першій HTML-відповіді й лишаються незмінними до кінця сесії.

Реєструйте їх у сервіс-провайдері через `Head::inertiaGlobals()`:

```php
use Laravel\Head\Facades\Head;
use Laravel\Head\HeadBuilder;

Head::inertiaGlobals(function (HeadBuilder $head) {
    $head
        ->viewport('width=device-width, initial-scale=1')
        ->colorScheme('light dark')
        ->icon('/favicon.svg', type: 'image/svg+xml')
        ->appleTouchIcon('/apple-touch-icon.png', sizes: '180x180')
        ->manifest('/site.webmanifest');
});
```

Глобальні значення Inertia не входять до пропа `head`, рендеряться без атрибутів власності `data-inertia` і ніколи не оновлюються після першої відповіді. Вони пасують для стабільних підказок браузера: viewport, колірної схеми, фавіконок, touch-іконок і маніфестів. Якщо тег специфічний для сторінки, важливий для SEO або може бути перекритий пізніше, розміщуйте його у `defaults`, метаданих маршруту чи метаданих під час виконання.

Застосунки, яким потрібні розв'язані метадані у вигляді структурованих даних, а не відрендерених тегів, можуть викликати `Head::toArray()`. Повернуті дані містять заголовки, значення Open Graph, схеми JSON-LD та інші розв'язані метадані.
