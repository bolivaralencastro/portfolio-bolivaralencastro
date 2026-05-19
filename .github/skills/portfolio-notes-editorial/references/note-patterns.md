# Note Patterns

Use these patterns inside `now.html`.

## Text note

```html
<article id="nota-2026-05-19-contexto-ia" class="note h-entry">
  <header class="note-header">
    <time class="dt-published" datetime="2026-05-19">19 Mai 2026</time>
    <a class="u-url" href="/now.html#nota-2026-05-19-contexto-ia">permalink</a>
  </header>
  <div class="e-content">
    <p>Talvez a interface mais importante da IA seja o contexto que ela consegue carregar.</p>
  </div>
  <p class="note-tags"><span class="p-category">IA</span></p>
</article>
```

## Seed / rough idea

```html
<article id="nota-2026-05-19-ideia-em-aberto" class="note h-entry note-seed">
  <header class="note-header">
    <time class="dt-published" datetime="2026-05-19">19 Mai 2026</time>
    <a class="u-url" href="/now.html#nota-2026-05-19-ideia-em-aberto">permalink</a>
  </header>
  <div class="e-content">
    <p>Ideia para aprofundar: quando uma ferramenta reduz atrito, ela também muda o tipo de pergunta que parece razoável fazer.</p>
  </div>
  <p class="note-tags"><span class="p-category">Ideia em aberto</span></p>
</article>
```

## Commented link

Use `u-bookmark-of` for the cited item.

```html
<article id="nota-2026-05-19-link-indieweb" class="note h-entry">
  <header class="note-header">
    <time class="dt-published" datetime="2026-05-19">19 Mai 2026</time>
    <a class="u-url" href="/now.html#nota-2026-05-19-link-indieweb">permalink</a>
  </header>
  <div class="e-content">
    <p>Guardei este link porque ele trata publicação própria como infraestrutura cultural, não só como escolha técnica.</p>
    <p><a class="u-bookmark-of" href="https://indieweb.org/" rel="noopener noreferrer" target="_blank">IndieWeb</a></p>
  </div>
  <p class="note-tags"><span class="p-category">Link comentado</span></p>
</article>
```

## Video link note

Use a normal linked citation when embedding would add fragility.

```html
<article id="nota-2026-05-19-video-contexto" class="note h-entry">
  <header class="note-header">
    <time class="dt-published" datetime="2026-05-19">19 Mai 2026</time>
    <a class="u-url" href="/now.html#nota-2026-05-19-video-contexto">permalink</a>
  </header>
  <div class="e-content">
    <p>Este vídeo vale como referência porque mostra a diferença entre automação como atalho e automação como mudança de processo.</p>
    <p><a class="u-video" href="https://example.com/video" rel="noopener noreferrer" target="_blank">Assistir ao vídeo</a></p>
  </div>
  <p class="note-tags"><span class="p-category">Vídeo</span></p>
</article>
```

## Image note

```html
<article id="nota-2026-05-19-interface-contexto" class="note h-entry">
  <header class="note-header">
    <time class="dt-published" datetime="2026-05-19">19 Mai 2026</time>
    <a class="u-url" href="/now.html#nota-2026-05-19-interface-contexto">permalink</a>
  </header>
  <div class="e-content">
    <figure class="note-media">
      <img class="u-photo" src="/assets/images/notes/nota-2026-05-19-interface-contexto/contexto.webp" alt="Descrição concreta da imagem">
      <figcaption>Uma imagem também pode funcionar como hipótese de trabalho.</figcaption>
    </figure>
  </div>
  <p class="note-tags"><span class="p-category">Imagem</span></p>
</article>
```

## Photo carousel

Use one note for the whole photo group.

```html
<article id="nota-2026-05-19-sequencia-visual" class="note h-entry">
  <header class="note-header">
    <time class="dt-published" datetime="2026-05-19">19 Mai 2026</time>
    <a class="u-url" href="/now.html#nota-2026-05-19-sequencia-visual">permalink</a>
  </header>
  <div class="e-content">
    <p>Sequência de imagens para guardar uma hipótese visual antes que ela vire projeto ou post.</p>
    <div class="note-carousel" aria-label="Carrossel de fotos">
      <figure>
        <img class="u-photo" src="/assets/images/notes/nota-2026-05-19-sequencia-visual/01.webp" alt="Descrição da primeira foto">
        <figcaption>Primeiro enquadramento.</figcaption>
      </figure>
      <figure>
        <img class="u-photo" src="/assets/images/notes/nota-2026-05-19-sequencia-visual/02.webp" alt="Descrição da segunda foto">
        <figcaption>Variação do mesmo tema.</figcaption>
      </figure>
    </div>
  </div>
  <p class="note-tags"><span class="p-category">Carrossel</span></p>
</article>
```

Keep carousel behavior CSS-first where possible: horizontal scroll with snap is enough for the first version.

## Audio note

```html
<article id="nota-2026-05-19-audio-rascunho" class="note h-entry">
  <header class="note-header">
    <time class="dt-published" datetime="2026-05-19">19 Mai 2026</time>
    <a class="u-url" href="/now.html#nota-2026-05-19-audio-rascunho">permalink</a>
  </header>
  <div class="e-content">
    <p>Rascunho falado sobre uma ideia que talvez vire texto depois.</p>
    <audio class="u-audio" controls src="/assets/audio/notes/nota-2026-05-19-audio-rascunho/audio.m4a"></audio>
  </div>
  <p class="note-tags"><span class="p-category">Áudio</span></p>
</article>
```

## Local video note

```html
<article id="nota-2026-05-19-video-rascunho" class="note h-entry">
  <header class="note-header">
    <time class="dt-published" datetime="2026-05-19">19 Mai 2026</time>
    <a class="u-url" href="/now.html#nota-2026-05-19-video-rascunho">permalink</a>
  </header>
  <div class="e-content">
    <p>Pequeno teste visual para registrar uma direção antes de elaborar.</p>
    <video class="u-video" controls src="/assets/video/notes/nota-2026-05-19-video-rascunho/video.mp4"></video>
  </div>
  <p class="note-tags"><span class="p-category">Vídeo</span></p>
</article>
```
