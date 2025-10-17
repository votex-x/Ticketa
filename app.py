from flask import Flask, request, jsonify
from flask_cors import CORS
import discord
from discord.ext import commands
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
import os
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
CORS(app)  # Permite acesso de qualquer domínio

# Thread pool para operações assíncronas
executor = ThreadPoolExecutor(max_workers=10)

class DiscordBotManager:
    def __init__(self):
        self.active_bots = {}
    
    async def create_bot_instance(self, token):
        """Cria uma instância temporária do bot"""
        intents = discord.Intents.all()
        bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
        
        # Cache de dados
        bot.cache_data = {}
        bot.token = token
        
        @bot.event
        async def on_ready():
            print(f'Bot {bot.user.name} conectado temporariamente')
        
        return bot
    
    async def get_guild_data(self, token, guild_id):
        """Obtém dados do servidor usando token temporário"""
        try:
            bot = await self.create_bot_instance(token)
            
            # Função para rodar o bot temporariamente
            async def run_temp_bot():
                try:
                    await bot.start(token)
                except Exception as e:
                    print(f"Erro no bot: {e}")
            
            # Inicia o bot em background
            bot_task = asyncio.create_task(run_temp_bot())
            
            # Aguarda o bot ficar pronto
            await asyncio.sleep(5)
            
            if not bot.is_ready():
                return {"error": "Bot não conseguiu conectar"}
            
            guild = bot.get_guild(int(guild_id))
            if not guild:
                await bot.close()
                return {"error": "Servidor não encontrado ou bot não está no servidor"}
            
            # Coleta dados completos
            data = await self.analyze_guild(guild)
            
            # Fecha a conexão do bot
            await bot.close()
            
            return data
            
        except Exception as e:
            return {"error": f"Erro na análise: {str(e)}"}
    
    async def analyze_guild(self, guild):
        """Análise completa do servidor"""
        
        # Dados básicos
        members = guild.members
        bots = [m for m in members if m.bot]
        humans = [m for m in members if not m.bot]
        online_members = [m for m in humans if m.status != discord.Status.offline]
        
        # Análise de cargos
        roles_analysis = []
        for role in sorted(guild.roles, key=lambda x: x.position, reverse=True):
            if len(role.members) > 0 and not role.is_default():
                roles_analysis.append({
                    "name": role.name,
                    "id": str(role.id),
                    "members_count": len(role.members),
                    "color": str(role.color),
                    "position": role.position
                })
        
        # Análise de canais
        text_channels = []
        voice_channels = []
        
        for channel in guild.channels:
            channel_data = {
                "name": channel.name,
                "id": str(channel.id),
                "position": channel.position
            }
            
            if isinstance(channel, discord.TextChannel):
                channel_data["type"] = "text"
                channel_data["nsfw"] = channel.nsfw
                text_channels.append(channel_data)
            elif isinstance(channel, discord.VoiceChannel):
                channel_data["type"] = "voice"
                channel_data["members_in_voice"] = len(channel.members)
                voice_channels.append(channel_data)
        
        # Análise de emojis
        emojis_analysis = {
            "static": [{"name": e.name, "url": str(e.url)} for e in guild.emojis if not e.animated],
            "animated": [{"name": e.name, "url": str(e.url)} for e in guild.emojis if e.animated],
            "total": len(guild.emojis),
            "limits": {
                "max_emojis": guild.emoji_limit,
                "available_slots": guild.emoji_limit - len(guild.emojis)
            }
        }
        
        # Estatísticas de engajamento
        member_activity = {
            "online": len(online_members),
            "idle": len([m for m in members if m.status == discord.Status.idle]),
            "dnd": len([m for m in members if m.status == discord.Status.dnd]),
            "offline": len([m for m in members if m.status == discord.Status.offline])
        }
        
        # Cálculos de porcentagem
        total_humans = len(humans)
        engagement_percentage = round((len(online_members) / total_humans * 100), 2) if total_humans > 0 else 0
        
        return {
            "server_info": {
                "name": guild.name,
                "id": str(guild.id),
                "owner": {
                    "name": str(guild.owner),
                    "id": str(guild.owner.id)
                } if guild.owner else None,
                "created_at": guild.created_at.isoformat(),
                "icon_url": str(guild.icon.url) if guild.icon else None,
                "banner_url": str(guild.banner.url) if guild.banner else None,
                "description": guild.description,
                "verification_level": str(guild.verification_level),
                "premium_tier": guild.premium_tier,
                "boost_count": guild.premium_subscription_count
            },
            "members": {
                "total": len(members),
                "humans": len(humans),
                "bots": len(bots),
                "activity": member_activity,
                "breakdown": {
                    "humans_percentage": round((len(humans) / len(members)) * 100, 2),
                    "bots_percentage": round((len(bots) / len(members)) * 100, 2)
                }
            },
            "engagement": {
                "online_percentage": engagement_percentage,
                "activity_score": self.calculate_activity_score(member_activity),
                "health_status": "healthy" if engagement_percentage > 30 else "moderate" if engagement_percentage > 15 else "low"
            },
            "channels": {
                "text": {
                    "count": len(text_channels),
                    "list": text_channels[:10]  # Limita para não ficar muito grande
                },
                "voice": {
                    "count": len(voice_channels),
                    "list": voice_channels[:10]
                },
                "categories": len(guild.categories),
                "total": len(guild.channels)
            },
            "roles": {
                "total": len(guild.roles),
                "list": roles_analysis[:15],  # Limita para não ficar muito grande
                "hierarchy": [role.name for role in sorted(guild.roles, key=lambda x: x.position, reverse=True)][:10]
            },
            "emojis": emojis_analysis,
            "features": {
                "server_features": list(guild.features),
                "premium_features": [
                    "banner" if guild.banner else None,
                    "vanity_url" if guild.vanity_url else None,
                    "boosted" if guild.premium_tier > 0 else None
                ]
            },
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def calculate_activity_score(self, activity):
        """Calcula score de atividade baseado nos membros online"""
        total_active = activity["online"] + activity["idle"] + activity["dnd"]
        return min(100, round((total_active / max(1, activity["offline"])) * 100, 2))

# Instância global do gerenciador
bot_manager = DiscordBotManager()

# Rotas da API Pública
@app.route('/')
def home():
    return jsonify({
        "message": "🚀 Discord Public Analytics API",
        "version": "2.0.0",
        "description": "API 100% pública - Cada bot usa seu próprio token",
        "endpoints": {
            "server_analysis": "POST /api/analyze",
            "health_check": "GET /api/health",
            "docs": "GET /api/docs"
        },
        "usage_example": {
            "method": "POST",
            "url": "/api/analyze",
            "body": {
                "token": "SEU_BOT_TOKEN",
                "guild_id": "123456789"
            }
        }
    })

@app.route('/api/analyze', methods=['POST'])
def analyze_server():
    """Endpoint principal - Análise completa do servidor"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "JSON body é obrigatório"}), 400
        
        token = data.get('token')
        guild_id = data.get('guild_id')
        
        if not token or not guild_id:
            return jsonify({
                "error": "Token e guild_id são obrigatórios",
                "received": {
                    "token_provided": bool(token),
                    "guild_id_provided": bool(guild_id)
                }
            }), 400
        
        # Executa a análise de forma assíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                bot_manager.get_guild_data(token, guild_id)
            )
            return jsonify(result)
        finally:
            loop.close()
            
    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check da API"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Discord Public Analytics API",
        "version": "2.0.0"
    })

@app.route('/api/docs', methods=['GET'])
def api_docs():
    """Documentação interativa da API"""
    return jsonify({
        "documentation": "Discord Public Analytics API - Docs",
        "base_url": "https://sua-api.herokuapp.com",
        "authentication": "Cada request envia o token do bot no body",
        "endpoints": {
            "POST /api/analyze": {
                "description": "Análise completa de um servidor Discord",
                "parameters": {
                    "token": "Token do bot Discord (obrigatório)",
                    "guild_id": "ID do servidor (obrigatório)"
                },
                "example_request": {
                    "token": "seu_bot_token_aqui",
                    "guild_id": "123456789012345678"
                },
                "example_response": "Inclui dados de membros, canais, cargos, emojis, etc."
            },
            "GET /api/health": {
                "description": "Status da API"
            }
        },
        "rate_limiting": "Sem limites para uso público (use com responsabilidade)",
        "open_source": "https://github.com/seu-usuario/discord-public-api"
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint não encontrado"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Erro interno do servidor"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)      } catch (e) {
        return addLog('Embed fields JSON inválido.');
      }
    }
    // push command into Firebase Realtime DB under /commands/<guildId>/<uuid>
    const cmdId = Math.random().toString(36).slice(2,10);
    const path = `/commands/${guildId}/${cmdId}`;
    await firebase.database().ref(path).set(payload);
    addLog('Pedido enviado: ' + cmdId);
  } catch (e) {
    console.error(e);
    addLog('Erro ao enviar pedido: ' + e.message);
  }
});
