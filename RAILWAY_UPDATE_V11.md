# Atualização v11 — Navegação lateral

Esta versão mantém a arquitetura Railway/PostgreSQL da v10 e altera principalmente a experiência do portal.

## Novidades
- Sidebar pública fixa no desktop e recolhível no celular.
- Header reduzida, focada na identidade UNIG/FP&A e acesso administrativo.
- Página exclusiva `\/tutoriais` para links cadastrados em **Vídeos Tutoriais**.
- Página exclusiva `\/bancos` para links cadastrados em **Bancos mais utilizados**.
- Home deixa de misturar esses dois grupos com as ferramentas gerais.
- `init-db` cria as novas categorias em bancos existentes e move links iniciados por “Banco de ...” para a seção de bancos.
- Conteúdo continua 100% administrável pelo painel existente.

## Deploy
Não há nova variável de ambiente e não há migração manual. O Pre-Deploy Command já existente executa `init-db` e aplica a atualização automaticamente.

Para cadastrar os links: **Administração → Gerenciar acessos → Novo acesso** e selecione a categoria desejada.
