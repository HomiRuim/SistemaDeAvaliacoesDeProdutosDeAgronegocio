// Atualização do JavaScript para corrigir o sistema de avaliações
// Adicione este código ao final do arquivo index.html, antes do </script> final

// Função modificada para enviar avaliação
document.getElementById('enviarAvaliacaoBtn').addEventListener('click', function() {
    const produtoId = document.getElementById('produtoIdInput').value;
    const pontuacao = document.getElementById('pontuacaoSelect').value;
    const comentario = document.getElementById('comentarioTextarea').value;
    
    // Mostrar indicador de carregamento
    this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Enviando...';
    this.disabled = true;
    
    fetch('/api/avaliar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            produto_id: produtoId,
            pontuacao: pontuacao,
            comentario: comentario
        })
    })
    .then(response => response.json())
    .then(data => {
        // Restaurar botão
        this.innerHTML = 'Enviar Avaliação';
        this.disabled = false;
        
        if (data.success) {
            // Fechar modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('avaliacaoModal'));
            modal.hide();
            
            // Limpar campos
            document.getElementById('comentarioTextarea').value = '';
            
            // Mostrar alerta de sucesso
            alert('Avaliação enviada com sucesso! A média atualizada é: ' + data.media.toFixed(1));
            
            // Recarregar produtos e recomendações com um pequeno atraso
            // para garantir que o banco de dados foi atualizado
            setTimeout(() => {
                carregarProdutos();
                carregarRecomendacoes();
            }, 500);
        } else {
            alert('Erro ao enviar avaliação: ' + (data.error || 'Erro desconhecido'));
        }
    })
    .catch(error => {
        // Restaurar botão
        this.innerHTML = 'Enviar Avaliação';
        this.disabled = false;
        
        console.error('Erro ao enviar avaliação:', error);
        alert('Erro ao enviar avaliação. Verifique o console para mais detalhes.');
    });
});
