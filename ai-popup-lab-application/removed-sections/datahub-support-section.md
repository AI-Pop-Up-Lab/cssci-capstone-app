# Removed: "Support the Research" section (Data Hub page)

Removed 2026-08-24, stored here for later restore. Contains everything needed
to bring the donate/support section back: JSX, CSS, and locale keys.

## 1. JSX — `src/pages/dataHubPage.js`

Insert after the `#datahub-stratification-frames` div, before the closing `</div>` of `.DataHubPage`:

```jsx
        <div className='datahub-colour-transition' id="light-to-white"></div>

        <div id="datahub-support">
            <h1>{t('datahubPage.support.title')}</h1>
            <p>{t('datahubPage.support.text1')}</p>
            <p>{t('datahubPage.support.text2')}</p>
            <button>{t('datahubPage.support.donate')}</button>
        </div>
```

## 2. CSS — `src/pages/dataHubPage.css`

### Base rules (place after the `#pink-to-light` transition rule / near other section styles)

```css
.datahub-colour-transition#light-to-white{
    background: #9BA9B0;
    background: linear-gradient(180deg, rgba(155, 169, 176, 1) 0%, rgba(209, 227, 221, 1) 100%);
}

#datahub-support{
    width: calc(100% - 8%);
    padding: 0 4%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

#datahub-support > h1{
    font-weight: 500;
    font-size: 34px;
    margin-bottom: 20px;
    text-align: center;
}

#datahub-support > p{
    font-size: 16px;
    max-width: 500px;
    text-align: center;
    margin-bottom: 20px;
    color: #9BA9B0;
}

#datahub-support > button{
    margin-bottom: 50px;
    color: #335058;
    background-color: #FCBFB7;
    font-family: 'unbounded';
    font-size: 16px;
    border: 2px solid #335058;
    border-radius: 18px;
    padding: 12px 46px;
}

#datahub-support > button:hover{
    cursor: pointer;
    background-color: #efb6af;
}
```

### Inside `@media screen and (max-width: 768px)` (breakpoint may differ — the first media block)

```css
    #datahub-support > h1{
        font-size: 30px;
    }

    #datahub-support > p {
        font-size: 14px;
    }

    #datahub-support > button{
        font-size: 14px;
    }
```

### Inside `@media screen and (max-width: 540px)`

```css
    #datahub-support > h1{
        font-size: 26px;
    }

    #datahub-support > p {
        font-size: 12px;
    }

    #datahub-support > button{
        font-size: 12px;
        padding: 8px 30px;
    }
```

### Inside `@media screen and (max-width: 450px)`

```css
    #datahub-support > h1{
        font-size: 20px;
    }

    #datahub-support > p {
        font-size: 10px;
    }

    #datahub-support > button{
        font-size: 10px;
        padding: 8px 30px;
    }
```

### Inside `@media screen and (max-width: 300px)`

```css
    #datahub-support > h1{
        font-size: 20px;
    }

    #datahub-support > p {
        font-size: 10px;
    }

    #datahub-support > button{
        font-size: 10px;
    }
```

## 3. Locale keys — add under `"datahubPage"` in each locale file

### `src/i18n/locales/en.json`

```json
        "support": {
            "title": "SUPPORT THE RESEARCH",
            "text1": "DONATE AND CONTRIBUTE TO THE FUTURE WORK OF THE PROJECT.",
            "text2": "ALL HELP WOULD BE GREATLY APPRECIATED",
            "donate": "DONATE"
        }
```

### `src/i18n/locales/nl.json`

```json
        "support": {
            "title": "STEUN HET ONDERZOEK",
            "text1": "DONEER EN DRAAG BIJ AAN DE TOEKOMSTIGE ACTIVITEITEN VAN HET PROJECT.",
            "text2": "ALLE HULP WORDT ZEER OP PRIJS GESTELD",
            "donate": "DONEER"
        }
```

### `src/i18n/locales/dk.json`

```json
        "support": {
            "title": "STØT FORSKNINGEN",
            "text1": "DONÉR OG BIDRAG TIL PROJEKTETS FREMTIDIGE ARBEJDE.",
            "text2": "AL HJÆLP VIL VÆRE MEGET VELKOMMEN",
            "donate": "DONÉR"
        }
```

### `src/i18n/locales/swe.json`

```json
        "support": {
            "title": "STÖD FORSKNINGEN",
            "text1": "DONERA OCH BIDRA TILL PROJEKTETS FRAMTIDA ARBETE.",
            "text2": "ALL HJÄLP ÄR MYCKET VÄLKOMMEN",
            "donate": "DONERA"
        }
```

Note: the donate button had no `onClick` handler yet — wiring up an actual
donation flow was still to-do when the section was removed.
