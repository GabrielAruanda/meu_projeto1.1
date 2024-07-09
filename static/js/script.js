// scripts.js

// Função para atualizar a página em tempo real
function atualizarPagina() {
    $.ajax({
        url: window.location.href, // URL da página atual
        type: 'GET',
        dataType: 'html', // Tipo de dados esperado (HTML neste caso)
        success: function(data) {
            // Atualiza apenas o conteúdo dentro do corpo da página
            $('body').html($(data).find('body').html());
        },
        error: function(xhr, status, error) {
            console.error('Erro ao atualizar página:', error);
        }
    });
}

$(document).ready(function() {
    // Evento de hover para a barra lateral
    $('#sidebar').hover(
        function() {
            $(this).removeClass('collapsed');
        },
        function() {
            $(this).addClass('collapsed');
        }
    );

    // Evento de clique para o botão de alternância da barra lateral
    $('.toggle-btn').click(function() {
        $('#sidebar').toggleClass('collapsed');
    });

    // Define um intervalo para chamar a função de atualização a cada 30 segundos (30000 milissegundos)
    setInterval(atualizarPagina, 30000); // Altere o intervalo conforme necessário
});
