Source: https://bolivaralencastro.com.br/blog/janelas-de-profundidade-parallax-facial-no-navegador.html

# Janelas de profundidade: paralaxe com rastreamento facial no navegador 

 Por [Bolívar Alencastro](https://bolivaralencastro.com.br/about.html) 05 Set 2026 • Creative Coding • WebGL • 6 min de leitura • [permalink](https://bolivaralencastro.com.br/blog/janelas-de-profundidade-parallax-facial-no-navegador.html)  

Construí uma técnica de renderização que transforma a tela do computador numa janela de verdade: a webcam segue a posição da sua cabeça e a cena 3D recalcula a perspectiva a cada quadro, com sombra do seu próprio corpo caindo sobre o cenário. 

 

Resposta rápida 

A ilusão vem de duas peças: rastreamento facial por webcam (MediaPipe Face Landmarker) estimando onde estão seus olhos, e uma projeção de frustum assimétrico (a técnica de Kooima) que redesenha a câmera 3D a cada quadro como se a tela fosse uma janela fixa. Tudo roda no navegador, em JavaScript puro, sem enviar nenhum quadro de vídeo a servidor algum. Ao longo do texto há três experiências ao vivo, uma por etapa — abra a câmera, mexa a cabeça, e feche antes de seguir para a próxima.  ![Ilustração editorial de uma janela 3D flutuante sobre fundo escuro, com grade de profundidade](https://bolivaralencastro.com.br/assets/images/blog/janelas-de-profundidade-parallax-facial-no-navegador/cover.webp) 

 

A ideia começou de uma pergunta simples: dá para fazer o monitor parar de ser uma imagem plana e passar a se comportar como uma janela real, com profundidade e paralaxe, sem headset e sem hardware especial? A resposta é sim, e a peça central não é nova — é uma técnica de projeção de 2009 que a computação gráfica usa há tempos em CAVEs e simuladores. O que mudou é que hoje ela cabe inteira num navegador, rodando sobre a própria webcam do usuário. 

## O truque não é mover a câmera. É deformar a lente. 

A primeira tentativa ingênua de "efeito 3D com webcam" costuma ser: pegar a posição da cabeça e mover a câmera virtual dentro da cena junto com ela. Isso produz um efeito de rotação, não de janela — a cena gira em torno de um eixo, mas não ganha profundidade real. O efeito de janela de verdade exige outra conta: a de **Robert Kooima**, descrita no relatório técnico *Generalized Perspective Projection* (2009), que trata a tela como um retângulo fixo no espaço e recalcula, a cada posição do olho, um frustum de câmera assimétrico — a pirâmide de visão que a GPU usa para projetar a cena não fica mais centrada, ela se inclina para compensar de onde você está olhando. 

Isso é exatamente o mesmo princípio por trás da demonstração de [Johnny Chung Lee com o sensor infravermelho do Wii Remote](http://johnnylee.net/projects/wii/), que popularizou a ideia de "realidade virtual de mesa" em 2007: um sensor barato rastreando a cabeça, e o resto é matemática de projeção. A diferença é que, hoje, o sensor infravermelho dedicado virou uma webcam comum e um modelo de rastreamento facial rodando via WebAssembly. 

Antes de seguir para a próxima peça, vale ver essa deformação de frustum funcionando — e vale ver num ambiente que você reconhece, não num cubo genérico. Um cenário abstrato deixa a matemática óbvia, mas esconde o efeito de verdade: um espaço reconhecível é o que deixa claro quando um canto "está errado" e quando ele volta a fazer sentido conforme você se move. A caixa abaixo é um quarto, livremente inspirado no quarto de Van Gogh em Arles. 

 

  

  

Processado localmente no seu navegador. Nenhum vídeo é enviado a servidores.   

 

O quarto em Arles — cama, criado-mudo, cadeiras, janela ao fundo. Vire a cabeça para conferir o canto.  

Esta experiência exige JavaScript e acesso à câmera para funcionar. 

## A peça que faltava: rastreamento facial sem instalar nada 

Para estimar onde estão seus olhos, uso o [Face Landmarker do MediaPipe](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker), um modelo que roda inteiramente no navegador (WebAssembly + GPU delegate) e devolve os pontos da íris a cada quadro de vídeo. A distância entre os cantos externos dos olhos, em pixels, vira uma estimativa de distância até a tela; a posição do centro dos olhos vira deslocamento lateral e vertical. Com isso, a cada frame eu tenho uma posição 3D aproximada da cabeça do visitante, em centímetros, relativa ao centro da tela — e é essa posição que alimenta a projeção assimétrica renderizada com [Three.js](https://threejs.org/). 

A camada final, que fecha a ilusão, é a sombra. Um corpo (uma cabeça e ombros simplificados) segue essa mesma posição rastreada, mas fica num layer de renderização que a câmera principal nunca desenha — só a luz enxerga esse layer ao calcular seu mapa de sombra. O resultado é uma sombra real, projetada no piso e na parede da cena, que se move e cresce conforme você se aproxima da tela, sem que nenhuma forma extra apareça flutuando na sua frente. 

Essa segunda caixa troca o interior por um exterior: uma paisagem ao entardecer, colinas se perdendo na neblina até o horizonte. Não tem paredes — o próprio céu, desenhado como uma cúpula ao redor de toda a cena, garante que nunca falta o que ver, não importa para que canto você olhe. 

 

  

  

Processado localmente no seu navegador. Nenhum vídeo é enviado a servidores.   

 

Entardecer sobre o campo — a sombra do seu corpo cai sobre a grama em primeiro plano.  

Esta experiência exige JavaScript e acesso à câmera para funcionar. 

## Da janela do quarto ao horizonte de uma cidade 

As duas primeiras cenas são ambientes baixos e horizontais — um quarto, um campo. A terceira inverte isso: uma rua à noite, prédios altos dos dois lados com janelas acesas em ritmo aleatório, recuando até uma lua no fundo. Mesmo motor de projeção e rastreamento, composição completamente diferente — profundidade vertical e densa, em vez de aberta. 

 

  

  

Processado localmente no seu navegador. Nenhum vídeo é enviado a servidores.   

 

Uma rua à noite — prédios recuando dos dois lados até a lua no horizonte.  

Esta experiência exige JavaScript e acesso à câmera para funcionar. 

## Uma janela por vez 

As três experiências deste post compartilham o mesmo motor de rastreamento, mas nunca ficam abertas ao mesmo tempo: abrir uma fecha automaticamente a anterior, libera a câmera e descarta a cena 3D da memória da GPU. Isso não é só economia de recursos — é a forma certa de pedir uma webcam num artigo. A câmera de quem lê não é um recurso de decoração; é confiança emprestada, e a interface precisa devolver o controle assim que a demonstração termina. 

## Onde isso serve, além de truque bonito 

Como Product Designer trabalhando entre fotografia e interface, o que me interessa aqui não é o efeito em si, mas o que ele deixa entrever: mostruários de produto que respondem à cabeça de quem olha, cenas ilustrativas de portfólio que ganham profundidade real sem depender de nenhum asset 3D pesado — só primitivas geométricas, luz e uma câmera bem calculada —, ou seções inteiras de um site que se comportam como espaços físicos em vez de imagens fixas. A técnica é barata em termos de infraestrutura: não existe servidor, não existe upload, é só matemática de projeção e um modelo de visão computacional rodando no dispositivo do visitante. 

 

## Referências 
 
- Robert Kooima, *Generalized Perspective Projection* (Louisiana State University, 2009) — a formulação do frustum assimétrico usada aqui. 
- [Johnny Chung Lee — Head Tracking for Desktop VR Displays using the Wii Remote](http://johnnylee.net/projects/wii/), a demonstração de 2007 que popularizou a técnica com hardware de consumo. 
- [MediaPipe Face Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker), o modelo de rastreamento facial que roda no navegador via WebAssembly. 
- [Three.js](https://threejs.org/), a biblioteca WebGL usada para renderizar as três cenas. 
  

 

Sobre o autor 

 ![Foto de Bolívar Alencastro](https://bolivaralencastro.com.br/assets/images/author/bolivar-alencastro.webp) 

 

### [Bolívar Alencastro](https://bolivaralencastro.com.br/about.html) 

Product Designer em São Paulo, cruzando fotografia, interface e código para testar até onde a tela deixa de ser plana quando alguém do outro lado está mesmo olhando. 
 
- [LinkedIn](https://www.linkedin.com/in/bolivaralencastro/) 
- [Instagram](https://www.instagram.com/bolivar.alencastro/) 
      

 

## Outras Publicações 

 [![Capa do post: Há Quedas Por Vir](https://bolivaralencastro.com.br/assets/images/blog/ha-quedas-por-vir/card.webp)](https://bolivaralencastro.com.br/blog/ha-quedas-por-vir.html) 

### [Há Quedas Por Vir](https://bolivaralencastro.com.br/blog/ha-quedas-por-vir.html) 

Um relato em cinco tempos sobre Há Quedas Por Vir, de Érica Storer e Sansa: shibari, um escritório suspenso e a queda que nunca chega.  

 [![Capa do post: A era da confiança: o novo jogo dos negócios em um mercado exausto](https://bolivaralencastro.com.br/assets/images/blog/state-economia-da-confianca/card.webp)](https://bolivaralencastro.com.br/blog/state-economia-da-confianca.html) 

### [A era da confiança: o novo jogo dos negócios em um mercado exausto](https://bolivaralencastro.com.br/blog/state-economia-da-confianca.html) 

No STATE, um painel sobre dados, autenticidade e confiança puxou uma reflexão sobre stalkers, pessoas amadas, bell hooks e o direito ao imprevisível.  

 [![Capa do post: A camerazinha de R$ 100 e a imagem suficiente](https://bolivaralencastro.com.br/assets/images/blog/a-camerazinha-de-100-reais-e-a-imagem-suficiente/card.webp)](https://bolivaralencastro.com.br/blog/a-camerazinha-de-100-reais-e-a-imagem-suficiente.html) 

### [A camerazinha de R$ 100 e a imagem suficiente](https://bolivaralencastro.com.br/blog/a-camerazinha-de-100-reais-e-a-imagem-suficiente.html) 

Uma câmera de até R$ 100, fotos de 2 MP e vídeo Full HD: um pequeno objeto que mostra o quanto a fabricação de imagens se tornou acessível.
